import logging
import os
import re
import shutil
import tempfile
import uuid
from pathlib import Path, PurePosixPath
from typing import Optional
from uuid import UUID

import PyPDF2
import uvicorn
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from auth import create_access_token, get_current_user, hash_password, verify_password
from config import settings
from database import get_db
from models import Dataset, User

# Generators
from generators.sft import generate_instruction_dataset
from generators.nl_sql import generate_nl2sql_dataset
from generators.rag import generate_rag_dataset
from generators.classification import generate_classification_dataset
from generators.code import generate_code_dataset
from generators.multilingual import generate_multilingual_dataset

# =====================================================
# Logging Setup
# =====================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# =====================================================
# Pydantic Schemas (response models — non-breaking)
# =====================================================


class DatasetResponse(BaseModel):
    message: str
    dataset_id: str


class MessageResponse(BaseModel):
    message: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    id: str
    email: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


# =====================================================
# App Init
# =====================================================

app = FastAPI(title="Dataset Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


# =====================================================
# Global Exception Handler
# =====================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled error on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# =====================================================
# Storage Config
# =====================================================

BASE_STORAGE_DIR = Path(settings.storage_dir)


def get_storage_path(storage_key: str) -> Path:
    return BASE_STORAGE_DIR / storage_key


def _sanitize_filename(filename: str | None) -> str:
    """Strip directory traversal components from an uploaded filename."""
    if not filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    safe_name = PurePosixPath(filename).name
    if not safe_name:
        raise HTTPException(status_code=400, detail="Invalid filename")
    return safe_name


def _save_upload_to_temp(upload: UploadFile, suffix: str = "") -> str:
    """Save an uploaded file to a secure temporary path and return the path."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        shutil.copyfileobj(upload.file, tmp)
    finally:
        tmp.close()
    return tmp.name


def create_dataset_context(dataset_type: str) -> tuple[UUID, str, Path]:
    """Create common dataset ID, storage key, and output path."""
    dataset_id = uuid.uuid4()
    storage_key = f"{dataset_type}/{dataset_id}.csv"
    output_path = get_storage_path(storage_key)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return dataset_id, storage_key, output_path


def save_dataset_metadata(
    db: Session,
    dataset_id: UUID,
    name: str,
    dataset_type: str,
    format: str,
    storage_key: str,
    user_id: UUID,
) -> None:
    new_dataset = Dataset(
        id=dataset_id,
        name=name,
        dataset_type=dataset_type,
        format=format,
        storage_key=storage_key,
        status="ready",
        user_id=user_id,
    )
    db.add(new_dataset)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


# =====================================================
# 1️⃣ SFT
# =====================================================

@app.post("/generate/sft", response_model=DatasetResponse)
def sft_dataset(
    topic: str = Form(...),
    model: str = Form(...),
    style: str = Form(...),
    num_pairs: int = Form(...),
    language: str = Form(...),
    temperature: float = Form(...),
    output_name: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    dataset_id, storage_key, output_path = create_dataset_context("sft")

    try:
        generate_instruction_dataset(
            topic=topic,
            output_csv_path=str(output_path),
            models=[model],
            style=style,
            num_samples=num_pairs,
            language=language,
            temperature=temperature,
        )
    except Exception as e:
        logger.error("SFT generation failed: %s", e)
        raise HTTPException(status_code=500, detail="Dataset generation failed")

    save_dataset_metadata(
        db, dataset_id, output_name, "sft", "csv", storage_key, current_user.id
    )

    return {"message": "SFT dataset generated successfully", "dataset_id": str(dataset_id)}


# =====================================================
# 2️⃣ NL-SQL
# =====================================================

@app.post("/generate/nl_sql", response_model=DatasetResponse)
def nl_sql_dataset(
    schema_file: UploadFile = File(...),
    output_name: str = Form(...),
    model: str = Form(...),
    num_samples: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    dataset_id, storage_key, output_path = create_dataset_context("nl_sql")

    safe_name = _sanitize_filename(schema_file.filename)
    schema_path = _save_upload_to_temp(schema_file, suffix=Path(safe_name).suffix)

    try:
        generate_nl2sql_dataset(
            schema_path=schema_path,
            output_path=str(output_path),
            model=model,
            num_samples=num_samples,
        )
    except Exception as e:
        logger.error("NL-SQL generation failed: %s", e)
        raise HTTPException(status_code=500, detail="Dataset generation failed")
    finally:
        # Clean up temp file
        if os.path.exists(schema_path):
            os.unlink(schema_path)

    save_dataset_metadata(
        db, dataset_id, output_name, "nl_sql", "csv", storage_key, current_user.id
    )

    return {"message": "NL-SQL dataset generated successfully", "dataset_id": str(dataset_id)}


# =====================================================
# 3️⃣ RAG-QA
# =====================================================

@app.post("/generate/rag_qa", response_model=DatasetResponse)
def rag_dataset(
    context_file: UploadFile = File(...),
    output_name: str = Form(...),
    model: str = Form(...),
    difficulty: str = Form(...),
    num_pairs: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    dataset_id, storage_key, output_path = create_dataset_context("rag_qa")

    safe_name = _sanitize_filename(context_file.filename)
    file_path = _save_upload_to_temp(context_file, suffix=Path(safe_name).suffix)

    try:
        if safe_name.endswith(".txt"):
            with open(file_path, "r", encoding="utf-8") as f:
                document_text = f.read()
        elif safe_name.endswith(".pdf"):
            reader = PyPDF2.PdfReader(file_path)
            document_text = ""
            for page in reader.pages:
                document_text += page.extract_text() + "\n"
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")

        generate_rag_dataset(
            document_text=document_text,
            output_path=str(output_path),
            model=model,
            difficulty=difficulty,
            max_pairs=num_pairs,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("RAG generation failed: %s", e)
        raise HTTPException(status_code=500, detail="Dataset generation failed")
    finally:
        if os.path.exists(file_path):
            os.unlink(file_path)

    save_dataset_metadata(
        db, dataset_id, output_name, "rag_qa", "csv", storage_key, current_user.id
    )

    return {"message": "RAG-QA dataset generated successfully", "dataset_id": str(dataset_id)}


# =====================================================
# 4️⃣ Classification
# =====================================================

@app.post("/generate/classification", response_model=DatasetResponse)
def classification_dataset(
    task_description: str = Form(...),
    output_name: str = Form(...),
    model: str = Form(...),
    num_samples: int = Form(...),
    class_labels: str = Form("class1,class2"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    dataset_id, storage_key, output_path = create_dataset_context("classification")

    labels = [label.strip() for label in class_labels.split(",") if label.strip()]
    if not labels:
        raise HTTPException(status_code=400, detail="class_labels must contain at least one label")

    try:
        generate_classification_dataset(
            task_description=task_description,
            class_labels=labels,
            output_path=str(output_path),
            model=model,
            num_samples=num_samples,
        )
    except Exception as e:
        logger.error("Classification generation failed: %s", e)
        raise HTTPException(status_code=500, detail="Dataset generation failed")

    save_dataset_metadata(
        db, dataset_id, output_name, "classification", "csv", storage_key, current_user.id
    )

    return {"message": "Classification dataset generated successfully", "dataset_id": str(dataset_id)}


# =====================================================
# 5️⃣ Text-to-Code
# =====================================================

@app.post("/generate/text_to_code", response_model=DatasetResponse)
def text_to_code_dataset(
    domain: str = Form(...),
    programming_language: str = Form(...),
    output_name: str = Form(...),
    model: str = Form(...),
    num_samples: int = Form(...),
    temperature: float = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    dataset_id, storage_key, output_path = create_dataset_context("text_to_code")

    try:
        generate_code_dataset(
            domain=domain,
            programming_language=programming_language,
            output_path=str(output_path),
            model=model,
            num_samples=num_samples,
            temperature=temperature,
        )
    except Exception as e:
        logger.error("Text-to-Code generation failed: %s", e)
        raise HTTPException(status_code=500, detail="Dataset generation failed")

    save_dataset_metadata(
        db, dataset_id, output_name, "text_to_code", "csv", storage_key, current_user.id
    )

    return {"message": "Text-to-Code dataset generated successfully", "dataset_id": str(dataset_id)}


# =====================================================
# 6️⃣ Multilingual
# =====================================================

@app.post("/generate/multilingual", response_model=DatasetResponse)
def multilingual_dataset(
    topic: str = Form(...),
    source_language: str = Form(...),
    destination_language: str = Form(...),
    output_name: str = Form(...),
    model: str = Form(...),
    temperature: float = Form(...),
    num_samples: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    dataset_id, storage_key, output_path = create_dataset_context("multilingual")

    try:
        generate_multilingual_dataset(
            topic=topic,
            source_language=source_language,
            target_language=destination_language,
            output_path=str(output_path),
            model=model,
            num_samples=num_samples,
            temperature=temperature,
        )
    except Exception as e:
        logger.error("Multilingual generation failed: %s", e)
        raise HTTPException(status_code=500, detail="Dataset generation failed")

    save_dataset_metadata(
        db, dataset_id, output_name, "multilingual", "csv", storage_key, current_user.id
    )

    return {"message": "Multilingual dataset generated successfully", "dataset_id": str(dataset_id)}


# =====================================================
# USER-SCOPED DATASET ROUTES
# =====================================================

@app.get("/datasets")
def list_datasets(
    dataset_type: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    datasets = db.query(Dataset).filter(
        Dataset.dataset_type == dataset_type,
        Dataset.user_id == current_user.id,
    ).all()

    return {
        "datasets": [
            {
                "id": str(d.id),
                "name": d.name,
                "format": d.format,
                "created_at": d.created_at,
            }
            for d in datasets
        ]
    }


@app.get("/datasets/{dataset_id}")
def get_dataset(
    dataset_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.user_id == current_user.id,
    ).first()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    file_path = get_storage_path(dataset.storage_key)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File missing")

    return FileResponse(path=file_path, media_type="text/csv", filename=f"{dataset.name}.csv")


@app.delete("/datasets/{dataset_id}", response_model=MessageResponse)
def delete_dataset(
    dataset_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.user_id == current_user.id,
    ).first()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    file_path = get_storage_path(dataset.storage_key)
    if file_path.exists():
        file_path.unlink()

    db.delete(dataset)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {"message": "Dataset deleted successfully"}


# =====================================================
# Auth Routes
# =====================================================

@app.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> dict:
    return {"id": str(current_user.id), "email": current_user.email}


@app.post("/register", response_model=MessageResponse)
def register(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)) -> dict:
    # Validate email format
    try:
        validated = RegisterRequest(email=email, password=password)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    existing_user = db.query(User).filter(User.email == validated.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=validated.email,
        hashed_password=hash_password(validated.password),
    )

    db.add(new_user)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    logger.info("New user registered: %s", validated.email)

    return {"message": "User registered successfully"}


@app.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> dict:
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning("Failed login attempt for: %s", form_data.username)
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    access_token = create_access_token(data={"sub": str(user.id)})

    logger.info("User logged in: %s", form_data.username)

    return {"access_token": access_token, "token_type": "bearer"}


# =====================================================
# Health Check
# =====================================================

@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}


# =====================================================
# Run Server
# =====================================================

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.debug)