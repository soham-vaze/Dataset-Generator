from typing import List, Optional, Tuple
from pathlib import Path
from uuid import UUID

from app.services.storage_service import StorageService
from domain.entities.dataset import DatasetEntity
from domain.interfaces.dataset_repository import DatasetRepositoryInterface


def list_datasets(
    dataset_type: str,
    user_id: UUID,
    dataset_repo: DatasetRepositoryInterface,
) -> List[DatasetEntity]:
    return dataset_repo.find_by_type_and_user(dataset_type, user_id)


def get_dataset(
    dataset_id: UUID,
    user_id: UUID,
    dataset_repo: DatasetRepositoryInterface,
) -> Optional[DatasetEntity]:
    return dataset_repo.find_by_id_and_user(dataset_id, user_id)


def delete_dataset(
    dataset_id: UUID,
    user_id: UUID,
    dataset_repo: DatasetRepositoryInterface,
    storage: StorageService,
) -> bool:
    entity = dataset_repo.find_by_id_and_user(dataset_id, user_id)
    if not entity:
        return False

    file_path = storage.get_storage_path(entity.storage_key)
    if file_path.exists():
        file_path.unlink()

    return dataset_repo.delete(dataset_id, user_id)
