from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from domain.entities.dataset import DatasetEntity


class DatasetRepositoryInterface(ABC):

    @abstractmethod
    def find_by_id_and_user(self, dataset_id: UUID, user_id: UUID) -> Optional[DatasetEntity]:
        pass

    @abstractmethod
    def find_by_type_and_user(self, dataset_type: str, user_id: UUID) -> List[DatasetEntity]:
        pass

    @abstractmethod
    def create(self, dataset: DatasetEntity) -> DatasetEntity:
        pass

    @abstractmethod
    def delete(self, dataset_id: UUID, user_id: UUID) -> bool:
        pass
