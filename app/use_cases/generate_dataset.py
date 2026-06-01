import logging
from typing import List, Union
from uuid import UUID

import PyPDF2

from domain.entities.dataset import DatasetEntity
from domain.interfaces.dataset_repository import DatasetRepositoryInterface

from generators.rag import generate_rag_dataset
from generators.classification import generate_classification_dataset
from generators.code import generate_code_dataset
from generators.multilingual import generate_multilingual_dataset
from generators.multilingual_ft import (
    generate_multilingual_ft_dataset,
    parse_language_pairs,
    DEFAULT_DOMAINS,
)

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def extract_document_text(file_path: str, filename: str) -> str:
    file_size = os.path.getsize(file_path)
    if file_size > MAX_FILE_SIZE:
        raise ValueError("File size exceeds the maximum limit of 50 MB")
    if filename.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    elif filename.endswith(".pdf"):
        reader = PyPDF2.PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    else:
        raise ValueError("Unsupported file format")


def _save_metadata(
    dataset_id: UUID,
    user_id: UUID,
    name: str,
    dataset_type: str,
    storage_key: str,
    dataset_repo: DatasetRepositoryInterface,
    status: str = "pending",
) -> None:
    entity = DatasetEntity(
        id=dataset_id,
        user_id=user_id,
        name=name,
        dataset_type=dataset_type,
        format="csv",
        storage_key=storage_key,
        status=status,
    )
    dataset_repo.create(entity)


def update_status(dataset_id: UUID, status: str) -> None:
    db = SessionLocal()
    try:
        db.query(Dataset).filter(Dataset.id == dataset_id).update({"status": status})
        db.commit()
    finally:
        db.close()


def run_generation_task(
    dataset_id: UUID,
    generator_fn: Callable[..., None],
    generator_kwargs: dict,
    cleanup_paths: list[str] | None = None,
) -> None:
    try:
        generator_fn(**generator_kwargs)
        update_status(dataset_id, "ready")
    except Exception as e:
        logger.error("Dataset generation failed for %s: %s", dataset_id, e)
        update_status(dataset_id, "failed")
    finally:
        for path in (cleanup_paths or []):
            if os.path.exists(path):
                os.unlink(path)


def generate_rag_qa_background(
    file_path: str,
    filename: str,
    output_path: str,
    model: str,
    difficulty: str,
    num_pairs: int,
) -> None:
    document_text = extract_document_text(file_path, filename)
    generate_rag_dataset(
        document_text=document_text,
        output_path=output_path,
        model=model,
        difficulty=difficulty,
        max_pairs=num_pairs,
    )

    _save_metadata(dataset_id, user_id, output_name, "rag_qa", storage_key, dataset_repo)
    return str(dataset_id)


def generate_classification(
    task_description: str,
    class_labels: list[str],
    output_name: str,
    model: str,
    num_samples: int,
    user_id: UUID,
    dataset_repo: DatasetRepositoryInterface,
    storage: StorageService,
) -> str:
    dataset_id, storage_key, output_path = storage.create_dataset_context("classification")

    generate_classification_dataset(
        task_description=task_description,
        class_labels=class_labels,
        output_path=str(output_path),
        model=model,
        num_samples=num_samples,
    )

    _save_metadata(dataset_id, user_id, output_name, "classification", storage_key, dataset_repo)
    return str(dataset_id)


def generate_text_to_code(
    domain: str,
    programming_language: str,
    output_name: str,
    model: str,
    num_samples: int,
    temperature: float,
    user_id: UUID,
    dataset_repo: DatasetRepositoryInterface,
    storage: StorageService,
) -> str:
    dataset_id, storage_key, output_path = storage.create_dataset_context("text_to_code")

    generate_code_dataset(
        domain=domain,
        programming_language=programming_language,
        output_path=str(output_path),
        model=model,
        num_samples=num_samples,
        temperature=temperature,
    )

    _save_metadata(dataset_id, user_id, output_name, "text_to_code", storage_key, dataset_repo)
    return str(dataset_id)


def generate_multilingual(
    topic: str,
    source_language: str,
    destination_languages: Union[str, List[str]],
    output_name: str,
    model: str,
    temperature: float,
    num_samples: int,
    user_id: UUID,
    dataset_repo: DatasetRepositoryInterface,
    storage: StorageService,
) -> str:
    dataset_id, storage_key, output_path = storage.create_dataset_context("multilingual")

    generate_multilingual_dataset(
        topic=topic,
        source_language=source_language,
        target_languages=destination_languages,
        output_path=str(output_path),
        model=model,
        num_samples=num_samples,
        temperature=temperature,
    )

    _save_metadata(dataset_id, user_id, output_name, "multilingual", storage_key, dataset_repo)
    return str(dataset_id)


def generate_multilingual_ft(
    training_pairs: str,
    zero_shot_pairs: str,
    domains: str,
    num_samples_per_pair: int,
    model: str,
    temperature: float,
    output_name: str,
    user_id: UUID,
    dataset_repo: DatasetRepositoryInterface,
    storage: StorageService,
) -> str:
    dataset_id, storage_key, output_path = storage.create_dataset_context("multilingual_ft")

    parsed_training = parse_language_pairs(training_pairs)
    parsed_zero_shot = parse_language_pairs(zero_shot_pairs) if zero_shot_pairs.strip() else []
    parsed_domains = (
        [d.strip() for d in domains.split(",") if d.strip()]
        if domains.strip()
        else list(DEFAULT_DOMAINS)
    )

    generate_multilingual_ft_dataset(
        training_pairs=parsed_training,
        zero_shot_pairs=parsed_zero_shot,
        domains=parsed_domains,
        output_path=str(output_path),
        model=model,
        num_samples_per_pair=num_samples_per_pair,
        temperature=temperature,
    )

    _save_metadata(dataset_id, user_id, output_name, "multilingual_ft", storage_key, dataset_repo)
    return str(dataset_id)
