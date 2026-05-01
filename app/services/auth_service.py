import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

logger = logging.getLogger(__name__)


class AuthService:
    """Handles password hashing, verification, and JWT token management.

    Framework-agnostic: no FastAPI or SQLAlchemy dependencies.
    """

    def __init__(self, secret_key: str, algorithm: str, expire_minutes: int):
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._expire_minutes = expire_minutes

    def hash_password(self, password: str) -> str:
        password_bytes = password.encode("utf-8")[:72]
        return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        password_bytes = plain_password.encode("utf-8")[:72]
        return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))

    def create_access_token(self, data: dict) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(minutes=self._expire_minutes)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, self._secret_key, algorithm=self._algorithm)

    def decode_token(self, token: str) -> Optional[uuid.UUID]:
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
            user_id: str | None = payload.get("sub")
            if user_id is None:
                return None
            return uuid.UUID(user_id)
        except JWTError:
            logger.warning("JWT decode failed for token")
            return None
