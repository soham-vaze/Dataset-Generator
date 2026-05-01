from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class UserEntity:
    id: UUID
    email: str
    hashed_password: str
    created_at: Optional[datetime] = None
