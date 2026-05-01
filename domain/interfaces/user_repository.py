from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from domain.entities.user import UserEntity


class UserRepositoryInterface(ABC):

    @abstractmethod
    def find_by_id(self, user_id: UUID) -> Optional[UserEntity]:
        pass

    @abstractmethod
    def find_by_email(self, email: str) -> Optional[UserEntity]:
        pass

    @abstractmethod
    def create(self, user: UserEntity) -> UserEntity:
        pass
