import logging
from uuid import UUID

import PyPDF2

from app.services.storage_service import StorageService
from domain.entities.dataset import DatasetEntity
from domain.interfaces.dataset_repository import DatasetRepositoryInterface

from generators.sft import generate_instruction_dataset
from generators.nl_sql import generate_nl2sql_dataset
from generators.rag import generate_rag_dataset
from generators.classification import generate_classification_dataset
from generators.code import generate_code_dataset
from generators.multilingual import generate_multilingual_dataset

logger = logging.getLogger(__name__)


def extract_document_text(file_path: str, filename: str) -> str:
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
) -> None:
    entity = DatasetEntity(
        id=dataset_id,
        user_id=user_id,
        name=name,
        dataset_type=dataset_type,
        format="csv",
        storage_key=storage_key,
    )
    dataset_repo.create(entity)


def generate_sft(
    topic: str,
    model: str,
    style: str,
    num_pairs: int,
    language: str,
    temperature: float,
    output_name: str,
    user_id: UUID,
    dataset_repo: DatasetRepositoryInterface,
    storage: StorageService,
) -> str:
    dataset_id, storage_key, output_path = storage.create_dataset_context("sft")

    generate_instruction_dataset(
        topic=topic,
        output_csv_path=str(output_path),
        models=[model],
        style=style,
        num_samples=num_pairs,
        language=language,
        temperature=temperature,
    )

    _save_metadata(dataset_id, user_id, output_name, "sft", storage_key, dataset_repo)
    return str(dataset_id)


def generate_nl_sql(
    schema_path: str,
    output_name: str,
    model: str,
    num_samples: int,
    user_id: UUID,
    dataset_repo: DatasetRepositoryInterface,
    storage: StorageService,
) -> str:
    dataset_id, storage_key, output_path = storage.create_dataset_context("nl_sql")

    generate_nl2sql_dataset(
        schema_path=schema_path,
        output_path=str(output_path),
        model=model,
        num_samples=num_samples,
    )

    _save_metadata(dataset_id, user_id, output_name, "nl_sql", storage_key, dataset_repo)
    return str(dataset_id)


def generate_rag_qa(
    file_path: str,
    filename: str,
    output_name: str,
    model: str,
    difficulty: str,
    num_pairs: int,
    user_id: UUID,
    dataset_repo: DatasetRepositoryInterface,
    storage: StorageService,
) -> str:
    document_text = extract_document_text(file_path, filename)

    dataset_id, storage_key, output_path = storage.create_dataset_context("rag_qa")

    generate_rag_dataset(
        document_text=document_text,
        output_path=str(output_path),
        model=model,
        difficulty=difficulty,
        max_pairs=num_pairs,
    )

    _save_metadata(dataset_id, user_id, output_name, "rag_qa", storage_key, dataset_repo)
    return str(dataset_id)


def generate_classification(
    task_description: str,
    class_labels: list,
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
    destination_language: str,
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
        target_language=destination_language,
        output_path=str(output_path),
        model=model,
        num_samples=num_samples,
        temperature=temperature,
    )

    _save_metadata(dataset_id, user_id, output_name, "multilingual", storage_key, dataset_repo)
    return str(dataset_id)
