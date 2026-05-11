import logging
import os
from typing import Any, Callable
from uuid import UUID

import PyPDF2

from domain.entities.dataset import DatasetEntity
from domain.interfaces.dataset_repository import DatasetRepositoryInterface

from generators.rag import generate_rag_dataset
from infrastructure.db.database import SessionLocal
from infrastructure.db.models import Dataset

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
