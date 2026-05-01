import logging
import uuid

from app.services.auth_service import AuthService
from domain.entities.user import UserEntity
from domain.interfaces.user_repository import UserRepositoryInterface

logger = logging.getLogger(__name__)


def register_user(
    email: str,
    password: str,
    user_repo: UserRepositoryInterface,
    auth_service: AuthService,
) -> UserEntity:
    existing = user_repo.find_by_email(email)
    if existing:
        raise ValueError("Email already registered")

    user = UserEntity(
        id=uuid.uuid4(),
        email=email,
        hashed_password=auth_service.hash_password(password),
    )
    created = user_repo.create(user)
    logger.info("New user registered: %s", email)
    return created


def login_user(
    email: str,
    password: str,
    user_repo: UserRepositoryInterface,
    auth_service: AuthService,
) -> str | None:
    user = user_repo.find_by_email(email)
    if not user or not auth_service.verify_password(password, user.hashed_password):
        return None
    token = auth_service.create_access_token(data={"sub": str(user.id)})
    logger.info("User logged in: %s", email)
    return token
