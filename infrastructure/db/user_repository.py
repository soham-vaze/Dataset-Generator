from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from domain.entities.user import UserEntity
from domain.interfaces.user_repository import UserRepositoryInterface
from infrastructure.db.models import User


class SqlAlchemyUserRepository(UserRepositoryInterface):

    def __init__(self, db: Session):
        self._db = db

    def _to_entity(self, user: User) -> UserEntity:
        return UserEntity(
            id=user.id,
            email=user.email,
            hashed_password=user.hashed_password,
            created_at=user.created_at,
        )

    def find_by_id(self, user_id: UUID) -> Optional[UserEntity]:
        user = self._db.query(User).filter(User.id == user_id).first()
        return self._to_entity(user) if user else None

    def find_by_email(self, email: str) -> Optional[UserEntity]:
        user = self._db.query(User).filter(User.email == email).first()
        return self._to_entity(user) if user else None

    def create(self, entity: UserEntity) -> UserEntity:
        user = User(
            id=entity.id,
            email=entity.email,
            hashed_password=entity.hashed_password,
        )
        self._db.add(user)
        try:
            self._db.commit()
            self._db.refresh(user)
        except Exception:
            self._db.rollback()
            raise
        return self._to_entity(user)
