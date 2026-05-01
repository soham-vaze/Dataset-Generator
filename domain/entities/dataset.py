from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class DatasetEntity:
    id: UUID
    user_id: UUID
    name: str
    dataset_type: str
    format: str
    storage_key: str
    status: str = "ready"
    created_at: Optional[datetime] = None
