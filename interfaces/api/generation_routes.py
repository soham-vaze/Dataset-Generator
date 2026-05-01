import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.services.storage_service import StorageService
from app.use_cases.generate_dataset import (
    generate_classification,
    generate_multilingual,
    generate_nl_sql,
    generate_rag_qa,
    generate_sft,
    generate_text_to_code,
)
from domain.entities.user import UserEntity
from domain.interfaces.dataset_repository import DatasetRepositoryInterface
from interfaces.api.dependencies import get_current_user, get_dataset_repo, storage_service
from interfaces.schemas.dataset import DatasetResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generate", tags=["generation"])


# =====================================================
# 1. SFT
# =====================================================

@router.post("/sft", response_model=DatasetResponse)
def sft_dataset(
    topic: str = Form(...),
    model: str = Form(...),
    style: str = Form(...),
    num_pairs: int = Form(...),
    language: str = Form(...),
    temperature: float = Form(...),
    output_name: str = Form(...),
    dataset_repo: DatasetRepositoryInterface = Depends(get_dataset_repo),
    current_user: UserEntity = Depends(get_current_user),
) -> dict:
    try:
        dataset_id = generate_sft(
            topic=topic,
            model=model,
            style=style,
            num_pairs=num_pairs,
            language=language,
            temperature=temperature,
            output_name=output_name,
            user_id=current_user.id,
            dataset_repo=dataset_repo,
            storage=storage_service,
        )
    except Exception as e:
        logger.error("SFT generation failed: %s", e)
        raise HTTPException(status_code=500, detail="Dataset generation failed")

    return {"message": "SFT dataset generated successfully", "dataset_id": dataset_id}


# =====================================================
# 2. NL-SQL
# =====================================================

@router.post("/nl_sql", response_model=DatasetResponse)
def nl_sql_dataset(
    schema_file: UploadFile = File(...),
    output_name: str = Form(...),
    model: str = Form(...),
    num_samples: int = Form(...),
    dataset_repo: DatasetRepositoryInterface = Depends(get_dataset_repo),
    current_user: UserEntity = Depends(get_current_user),
) -> dict:
    safe_name = storage_service.sanitize_filename(schema_file.filename)
    if not safe_name:
        raise HTTPException(status_code=400, detail="Invalid filename")

    schema_path = storage_service.save_upload_to_temp(schema_file, suffix=Path(safe_name).suffix)

    try:
        dataset_id = generate_nl_sql(
            schema_path=schema_path,
            output_name=output_name,
            model=model,
            num_samples=num_samples,
            user_id=current_user.id,
            dataset_repo=dataset_repo,
            storage=storage_service,
        )
    except Exception as e:
        logger.error("NL-SQL generation failed: %s", e)
        raise HTTPException(status_code=500, detail="Dataset generation failed")
    finally:
        storage_service.cleanup_temp_file(schema_path)

    return {"message": "NL-SQL dataset generated successfully", "dataset_id": dataset_id}


# =====================================================
# 3. RAG-QA
# =====================================================

@router.post("/rag_qa", response_model=DatasetResponse)
def rag_dataset(
    context_file: UploadFile = File(...),
    output_name: str = Form(...),
    model: str = Form(...),
    difficulty: str = Form(...),
    num_pairs: int = Form(...),
    dataset_repo: DatasetRepositoryInterface = Depends(get_dataset_repo),
    current_user: UserEntity = Depends(get_current_user),
) -> dict:
    safe_name = storage_service.sanitize_filename(context_file.filename)
    if not safe_name:
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = storage_service.save_upload_to_temp(context_file, suffix=Path(safe_name).suffix)

    try:
        dataset_id = generate_rag_qa(
            file_path=file_path,
            filename=safe_name,
            output_name=output_name,
            model=model,
            difficulty=difficulty,
            num_pairs=num_pairs,
            user_id=current_user.id,
            dataset_repo=dataset_repo,
            storage=storage_service,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("RAG generation failed: %s", e)
        raise HTTPException(status_code=500, detail="Dataset generation failed")
    finally:
        storage_service.cleanup_temp_file(file_path)

    return {"message": "RAG-QA dataset generated successfully", "dataset_id": dataset_id}


# =====================================================
# 4. Classification
# =====================================================

@router.post("/classification", response_model=DatasetResponse)
def classification_dataset(
    task_description: str = Form(...),
    output_name: str = Form(...),
    model: str = Form(...),
    num_samples: int = Form(...),
    class_labels: str = Form("class1,class2"),
    dataset_repo: DatasetRepositoryInterface = Depends(get_dataset_repo),
    current_user: UserEntity = Depends(get_current_user),
) -> dict:
    labels = [label.strip() for label in class_labels.split(",") if label.strip()]
    if not labels:
        raise HTTPException(status_code=400, detail="class_labels must contain at least one label")

    try:
        dataset_id = generate_classification(
            task_description=task_description,
            class_labels=labels,
            output_name=output_name,
            model=model,
            num_samples=num_samples,
            user_id=current_user.id,
            dataset_repo=dataset_repo,
            storage=storage_service,
        )
    except Exception as e:
        logger.error("Classification generation failed: %s", e)
        raise HTTPException(status_code=500, detail="Dataset generation failed")

    return {"message": "Classification dataset generated successfully", "dataset_id": dataset_id}


# =====================================================
# 5. Text-to-Code
# =====================================================

@router.post("/text_to_code", response_model=DatasetResponse)
def text_to_code_dataset(
    domain: str = Form(...),
    programming_language: str = Form(...),
    output_name: str = Form(...),
    model: str = Form(...),
    num_samples: int = Form(...),
    temperature: float = Form(...),
    dataset_repo: DatasetRepositoryInterface = Depends(get_dataset_repo),
    current_user: UserEntity = Depends(get_current_user),
) -> dict:
    try:
        dataset_id = generate_text_to_code(
            domain=domain,
            programming_language=programming_language,
            output_name=output_name,
            model=model,
            num_samples=num_samples,
            temperature=temperature,
            user_id=current_user.id,
            dataset_repo=dataset_repo,
            storage=storage_service,
        )
    except Exception as e:
        logger.error("Text-to-Code generation failed: %s", e)
        raise HTTPException(status_code=500, detail="Dataset generation failed")

    return {"message": "Text-to-Code dataset generated successfully", "dataset_id": dataset_id}


# =====================================================
# 6. Multilingual
# =====================================================

@router.post("/multilingual", response_model=DatasetResponse)
def multilingual_dataset(
    topic: str = Form(...),
    source_language: str = Form(...),
    destination_language: str = Form(...),
    output_name: str = Form(...),
    model: str = Form(...),
    temperature: float = Form(...),
    num_samples: int = Form(...),
    dataset_repo: DatasetRepositoryInterface = Depends(get_dataset_repo),
    current_user: UserEntity = Depends(get_current_user),
) -> dict:
    try:
        dataset_id = generate_multilingual(
            topic=topic,
            source_language=source_language,
            destination_language=destination_language,
            output_name=output_name,
            model=model,
            temperature=temperature,
            num_samples=num_samples,
            user_id=current_user.id,
            dataset_repo=dataset_repo,
            storage=storage_service,
        )
    except Exception as e:
        logger.error("Multilingual generation failed: %s", e)
        raise HTTPException(status_code=500, detail="Dataset generation failed")

    return {"message": "Multilingual dataset generated successfully", "dataset_id": dataset_id}
