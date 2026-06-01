import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile

from generators.classification import generate_classification_dataset
from generators.code import generate_code_dataset
from generators.multilingual import generate_multilingual_dataset
from generators.nl_sql import generate_nl2sql_dataset
from generators.sft import generate_instruction_dataset
from interfaces.utils.start_generate import start_generation
from app.use_cases.generate_dataset import (
    generate_classification,
    generate_multilingual,
    generate_multilingual_ft,
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
    background_tasks: BackgroundTasks,
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
    return start_generation(
        background_tasks, "sft", output_name, current_user.id, dataset_repo,
        generator_fn=generate_instruction_dataset,
        generator_kwargs=dict(topic=topic, models=[model], style=style,
                              num_samples=num_pairs, language=language, temperature=temperature),
    )

# =====================================================
# 2. NL-SQL
# =====================================================

@router.post("/nl_sql", response_model=DatasetResponse)
def nl_sql_dataset(
    background_tasks: BackgroundTasks,
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

    return start_generation(
        background_tasks, "nl_sql", output_name, current_user.id, dataset_repo,
        generator_fn=generate_nl2sql_dataset,
        generator_kwargs=dict(schema_path=schema_path, model=model, num_samples=num_samples),
        cleanup_paths=[schema_path],
    )

# =====================================================
# 3. RAG-QA
# =====================================================

@router.post("/rag_qa", response_model=DatasetResponse)
def rag_dataset(
    background_tasks: BackgroundTasks,
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

    return start_generation(
        background_tasks, "rag_qa", output_name, current_user.id, dataset_repo,
        generator_fn=generate_rag_qa_background,
        generator_kwargs=dict(file_path=file_path, filename=safe_name,
                              model=model, difficulty=difficulty, num_pairs=num_pairs),
        cleanup_paths=[file_path],
    )

# =====================================================
# 4. Classification
# =====================================================

@router.post("/classification", response_model=DatasetResponse)
def classification_dataset(
    background_tasks: BackgroundTasks,
    task_description: str = Form(...),
    output_name: str = Form(...),
    model: str = Form(...),
    num_samples: int = Form(...),
    class_labels: str = Form("class1,class2"),
    dataset_repo: DatasetRepositoryInterface = Depends(get_dataset_repo),
    current_user: UserEntity = Depends(get_current_user),
) -> dict:
    
    labels = [label.strip() for label in class_labels.split(",") if label.strip()]

    # Remove duplicates while preserving order
    seen = set()
    unique_labels = []
    for label in labels:
        lower = label.lower()
        if lower not in seen:
            seen.add(lower)
            unique_labels.append(label)
    labels = unique_labels

    if len(labels) < 2:
        raise HTTPException(status_code=400, detail="At least 2 unique labels are required")

    if len(labels) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 labels allowed")

    for label in labels:
        if len(label) > 100:
            raise HTTPException(status_code=400, detail=f"Label too long (max 100 chars): '{label[:20]}...'")
        if not all(c.isalnum() or c in "-_ " for c in label):
            raise HTTPException(status_code=400, detail=f"Label contains invalid characters: '{label}'")

    return start_generation(
        background_tasks, "classification", output_name, current_user.id, dataset_repo,
        generator_fn=generate_classification_dataset,
        generator_kwargs=dict(task_description=task_description, class_labels=labels,
                              model=model, num_samples=num_samples)
    )


# =====================================================
# 5. Text-to-Code
# =====================================================

@router.post("/text_to_code", response_model=DatasetResponse)
def text_to_code_dataset(
    background_tasks: BackgroundTasks,
    domain: str = Form(...),
    programming_language: str = Form(...),
    output_name: str = Form(...),
    model: str = Form(...),
    num_samples: int = Form(...),
    temperature: float = Form(...),
    dataset_repo: DatasetRepositoryInterface = Depends(get_dataset_repo),
    current_user: UserEntity = Depends(get_current_user),
) -> dict:
    return start_generation(
        background_tasks, "text_to_code", output_name, current_user.id, dataset_repo,
        generator_fn=generate_code_dataset,
        generator_kwargs=dict(domain=domain, programming_language=programming_language,
                              model=model, num_samples=num_samples, temperature=temperature),
    )


# =====================================================
# 6. Multilingual
# =====================================================

@router.post("/multilingual", response_model=DatasetResponse)
def multilingual_dataset(
    background_tasks: BackgroundTasks,
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
    # Parse and deduplicate the comma-separated target languages sent by the client.
    raw_languages = [lang.strip().lower() for lang in destination_language.split(",") if lang.strip()]

    seen: set = set()
    destination_languages: list = []
    for lang in raw_languages:
        if lang not in seen:
            seen.add(lang)
            destination_languages.append(lang)

    if not destination_languages:
        raise HTTPException(status_code=400, detail="At least one target language must be specified")

    if len(destination_languages) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 target languages allowed per request")

    try:
        dataset_id = generate_multilingual(
            topic=topic,
            source_language=source_language,
            destination_languages=destination_languages,
            output_name=output_name,
            model=model,
            temperature=temperature,
            num_samples=num_samples,
            user_id=current_user.id,
            dataset_repo=dataset_repo,
            storage=storage_service,
        )
    except ValueError as e:
        logger.warning("Multilingual validation error: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Multilingual generation failed: %s", e)
        raise HTTPException(status_code=500, detail="Dataset generation failed")

    return {"message": "Multilingual dataset generated successfully", "dataset_id": dataset_id}


# =====================================================
# 7. Multilingual Fine-Tuning
# =====================================================

@router.post("/multilingual_ft", response_model=DatasetResponse)
def multilingual_ft_dataset(
    training_pairs: str = Form(...),
    zero_shot_pairs: str = Form(""),
    domains: str = Form(""),
    num_samples_per_pair: int = Form(...),
    model: str = Form(...),
    temperature: float = Form(...),
    output_name: str = Form(...),
    dataset_repo: DatasetRepositoryInterface = Depends(get_dataset_repo),
    current_user: UserEntity = Depends(get_current_user),
) -> dict:
    if not training_pairs.strip():
        raise HTTPException(status_code=400, detail="At least one training pair is required")

    try:
        dataset_id = generate_multilingual_ft(
            training_pairs=training_pairs,
            zero_shot_pairs=zero_shot_pairs,
            domains=domains,
            num_samples_per_pair=num_samples_per_pair,
            model=model,
            temperature=temperature,
            output_name=output_name,
            user_id=current_user.id,
            dataset_repo=dataset_repo,
            storage=storage_service,
        )
    except ValueError as e:
        logger.warning("Multilingual FT validation error: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Multilingual FT generation failed: %s", e)
        raise HTTPException(status_code=500, detail="Dataset generation failed")

    return {"message": "Multilingual fine-tuning dataset generated successfully", "dataset_id": dataset_id}
