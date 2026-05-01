import logging
from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.services.auth_service import AuthService
from app.services.storage_service import StorageService
from domain.entities.user import UserEntity
from domain.interfaces.dataset_repository import DatasetRepositoryInterface
from domain.interfaces.user_repository import UserRepositoryInterface
from infrastructure.config.settings import settings
from infrastructure.db.database import SessionLocal
from infrastructure.db.dataset_repository import SqlAlchemyDatasetRepository
from infrastructure.db.user_repository import SqlAlchemyUserRepository

logger = logging.getLogger(__name__)

# =====================================================
# Singleton service instances (wired with config)
# =====================================================

auth_service = AuthService(
    secret_key=settings.jwt_secret_key,
    algorithm=settings.jwt_algorithm,
    expire_minutes=settings.access_token_expire_minutes,
)

storage_service = StorageService(base_dir=settings.storage_dir)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# =====================================================
# FastAPI dependency providers
# =====================================================

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user_repo(db: Session = Depends(get_db)) -> UserRepositoryInterface:
    return SqlAlchemyUserRepository(db)


def get_dataset_repo(db: Session = Depends(get_db)) -> DatasetRepositoryInterface:
    return SqlAlchemyDatasetRepository(db)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> UserEntity:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user_id = auth_service.decode_token(token)
    if user_id is None:
        raise credentials_exception

    user_repo = SqlAlchemyUserRepository(db)
    user = user_repo.find_by_id(user_id)
    if user is None:
        logger.warning("User not found for id: %s", user_id)
        raise credentials_exception

    return user
