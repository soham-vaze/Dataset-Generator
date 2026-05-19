from typing import Any

from fastapi import BackgroundTasks
from sqlalchemy import UUID

from app.services import storage_service
from app.use_cases.generate_dataset import _save_metadata, run_generation_task
from domain.interfaces.dataset_repository import DatasetRepositoryInterface
from interfaces.api.dependencies import storage_service


def start_generation(
    background_tasks: BackgroundTasks,
    dataset_type: str,
    output_name: str,
    user_id: UUID,
    dataset_repo: DatasetRepositoryInterface,
    generator_fn,
    generator_kwargs: dict,
    cleanup_paths: list[str] | None = None
) -> dict:
    dataset_id, storage_key, output_path = storage_service.create_dataset_context(dataset_type)
    generator_kwargs["output_path"] = str(output_path)

    _save_metadata(dataset_id, user_id, output_name, dataset_type, storage_key, dataset_repo, status="pending")

    background_tasks.add_task(
        run_generation_task, dataset_id, generator_fn, generator_kwargs,
        cleanup_paths=cleanup_paths,
    )

    return {"message": f"{dataset_type} generation started", "dataset_id": str(dataset_id)}
