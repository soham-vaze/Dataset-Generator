import os
import shutil
import uuid
from uuid import UUID
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, Depends, Query, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
import uvicorn

from database import get_db
from models import Dataset, User
from auth import hash_password, verify_password, create_access_token, get_current_user
from fastapi.security import OAuth2PasswordRequestForm

# Generators
from generators.sft import generate_instruction_dataset
from generators.nl_sql import generate_nl2sql_dataset
from generators.rag import generate_rag_dataset
from generators.classification import generate_classification_dataset
from generators.code import generate_code_dataset
from generators.multilingual import generate_multilingual_dataset

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Dataset Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# Storage Config
# =====================================================

BASE_STORAGE_DIR = Path("local_storage")


def get_storage_path(storage_key: str):
    return BASE_STORAGE_DIR / storage_key


def save_dataset_metadata(
    db: Session,
    dataset_id: UUID,
    name: str,
    dataset_type: str,
    format: str,
    storage_key: str,
    user_id: UUID
):
    new_dataset = Dataset(
        id=dataset_id,
        name=name,
        dataset_type=dataset_type,
        format=format,
        storage_key=storage_key,
        status="ready",
        user_id=user_id
    )
    db.add(new_dataset)
    db.commit()


# =====================================================
# 1️⃣ SFT
# =====================================================

@app.post("/generate/sft")
def sft_dataset(
    topic: str = Form(...),
    model: str = Form(...),
    style: str = Form(...),
    num_pairs: int = Form(...),
    language: str = Form(...),
    temperature: float = Form(...),
    output_name: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    dataset_id = uuid.uuid4()
    storage_key = f"sft/{dataset_id}.csv"
    output_path = get_storage_path(storage_key)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    generate_instruction_dataset(
        topic=topic,
        output_csv_path=str(output_path),
        models=[model],
        style=style,
        num_pairs=num_pairs,
        language=language,
        temperature=temperature
    )

    save_dataset_metadata(
        db, dataset_id, output_name, "sft", "csv", storage_key, current_user.id
    )

    return {"message": "SFT dataset generated successfully", "dataset_id": str(dataset_id)}


# =====================================================
# 2️⃣ NL-SQL
# =====================================================

@app.post("/generate/nl_sql")
async def nl_sql_dataset(
    schema_file: UploadFile = File(...),
    output_name: str = Form(...),
    model: str = Form(...),
    num_samples: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    dataset_id = uuid.uuid4()
    storage_key = f"nl_sql/{dataset_id}.csv"
    output_path = get_storage_path(storage_key)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    schema_path = f"/tmp/{schema_file.filename}"
    with open(schema_path, "wb") as buffer:
        shutil.copyfileobj(schema_file.file, buffer)

    generate_nl2sql_dataset(
        schema_path=schema_path,
        output_path=str(output_path),
        model=model,
        num_samples=num_samples
    )

    save_dataset_metadata(
        db, dataset_id, output_name, "nl_sql", "csv", storage_key, current_user.id
    )

    return {"message": "NL-SQL dataset generated successfully", "dataset_id": str(dataset_id)}


# =====================================================
# 3️⃣ RAG-QA
# =====================================================

@app.post("/generate/rag_qa")
async def rag_dataset(
    context_file: UploadFile = File(...),
    output_name: str = Form(...),
    model: str = Form(...),
    difficulty: str = Form(...),
    num_pairs: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    dataset_id = uuid.uuid4()
    storage_key = f"rag_qa/{dataset_id}.csv"
    output_path = get_storage_path(storage_key)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    file_path = f"/tmp/{context_file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(context_file.file, buffer)

    if file_path.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            document_text = f.read()
    elif file_path.endswith(".pdf"):
        import PyPDF2
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
        max_pairs=num_pairs
    )

    save_dataset_metadata(
        db, dataset_id, output_name, "rag_qa", "csv", storage_key, current_user.id
    )

    return {"message": "RAG-QA dataset generated successfully", "dataset_id": str(dataset_id)}


# =====================================================
# (Remaining generators updated same way)
# =====================================================

@app.post("/generate/classification")
def classification_dataset(
    task_description: str = Form(...),
    output_name: str = Form(...),
    model: str = Form(...),
    num_samples: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    dataset_id = uuid.uuid4()
    storage_key = f"classification/{dataset_id}.csv"
    output_path = get_storage_path(storage_key)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    generate_classification_dataset(
        task_description=task_description,
        class_labels=["class1", "class2"],
        output_path=str(output_path),
        model=model,
        num_samples=num_samples
    )

    save_dataset_metadata(
        db, dataset_id, output_name, "classification", "csv", storage_key, current_user.id
    )

    return {"message": "Classification dataset generated successfully", "dataset_id": str(dataset_id)}


@app.post("/generate/text_to_code")
def text_to_code_dataset(
    domain: str = Form(...),
    programming_language: str = Form(...),
    output_name: str = Form(...),
    model: str = Form(...),
    num_samples: int = Form(...),
    temperature: float = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    dataset_id = uuid.uuid4()
    storage_key = f"text_to_code/{dataset_id}.csv"
    output_path = get_storage_path(storage_key)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    generate_code_dataset(
        domain=domain,
        programming_language=programming_language,
        output_path=str(output_path),
        model=model,
        num_samples=num_samples,
        temperature=temperature
    )

    save_dataset_metadata(
        db, dataset_id, output_name, "text_to_code", "csv", storage_key, current_user.id
    )

    return {"message": "Text-to-Code dataset generated successfully", "dataset_id": str(dataset_id)}


@app.post("/generate/multilingual")
def multilingual_dataset(
    topic: str = Form(...),
    source_language: str = Form(...),
    destination_language: str = Form(...),
    output_name: str = Form(...),
    model: str = Form(...),
    temperature: float = Form(...),
    num_samples: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    dataset_id = uuid.uuid4()
    storage_key = f"multilingual/{dataset_id}.csv"
    output_path = get_storage_path(storage_key)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    generate_multilingual_dataset(
        topic=topic,
        source_language=source_language,
        target_language=destination_language,
        output_path=str(output_path),
        model=model,
        num_samples=num_samples,
        temperature=temperature
    )

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
    current_user: User = Depends(get_current_user)
):
    datasets = db.query(Dataset).filter(
        Dataset.dataset_type == dataset_type,
        Dataset.user_id == current_user.id
    ).all()

    return {
        "datasets": [
            {
                "id": str(d.id),
                "name": d.name,
                "format": d.format,
                "created_at": d.created_at
            }
            for d in datasets
        ]
    }


@app.get("/datasets/{dataset_id}")
def get_dataset(
    dataset_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.user_id == current_user.id
    ).first()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    file_path = get_storage_path(dataset.storage_key)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File missing")

    return FileResponse(path=file_path, media_type="text/csv", filename=f"{dataset.name}.csv")


@app.delete("/datasets/{dataset_id}")
def delete_dataset(
    dataset_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.user_id == current_user.id
    ).first()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    file_path = get_storage_path(dataset.storage_key)
    if file_path.exists():
        file_path.unlink()

    db.delete(dataset)
    db.commit()

    return {"message": "Dataset deleted successfully"}


# =====================================================
# AUTH ROUTES
# =====================================================

@app.post("/register")
def register(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=email,
        hashed_password=hash_password(password)
    )

    db.add(new_user)
    db.commit()

    return {"message": "User registered successfully"}


@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    access_token = create_access_token(data={"sub": str(user.id)})

    return {"access_token": access_token, "token_type": "bearer"}


# =====================================================
# Run Server
# =====================================================

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)