from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from domain.entities.dataset import DatasetEntity
from domain.interfaces.dataset_repository import DatasetRepositoryInterface
from infrastructure.db.models import Dataset


class SqlAlchemyDatasetRepository(DatasetRepositoryInterface):

    def __init__(self, db: Session):
        self._db = db

    def _to_entity(self, dataset: Dataset) -> DatasetEntity:
        return DatasetEntity(
            id=dataset.id,
            user_id=dataset.user_id,
            name=dataset.name,
            dataset_type=dataset.dataset_type,
            format=dataset.format,
            storage_key=dataset.storage_key,
            status=dataset.status,
            created_at=dataset.created_at,
        )

    def find_by_id_and_user(self, dataset_id: UUID, user_id: UUID) -> Optional[DatasetEntity]:
        dataset = self._db.query(Dataset).filter(
            Dataset.id == dataset_id,
            Dataset.user_id == user_id,
        ).first()
        return self._to_entity(dataset) if dataset else None

    def find_by_type_and_user(self, dataset_type: str, user_id: UUID) -> List[DatasetEntity]:
        datasets = self._db.query(Dataset).filter(
            Dataset.dataset_type == dataset_type,
            Dataset.user_id == user_id,
        ).all()
        return [self._to_entity(d) for d in datasets]

    def create(self, entity: DatasetEntity) -> DatasetEntity:
        dataset = Dataset(
            id=entity.id,
            name=entity.name,
            dataset_type=entity.dataset_type,
            format=entity.format,
            storage_key=entity.storage_key,
            status=entity.status,
            user_id=entity.user_id,
        )
        self._db.add(dataset)
        try:
            self._db.commit()
            self._db.refresh(dataset)
        except Exception:
            self._db.rollback()
            raise
        return self._to_entity(dataset)

    def delete(self, dataset_id: UUID, user_id: UUID) -> bool:
        dataset = self._db.query(Dataset).filter(
            Dataset.id == dataset_id,
            Dataset.user_id == user_id,
        ).first()
        if not dataset:
            return False
        self._db.delete(dataset)
        try:
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
        return True
