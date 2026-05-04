import os
import shutil
import tempfile
import uuid
from pathlib import Path, PurePosixPath
from typing import Tuple
from uuid import UUID


class StorageService:
    """Manages file storage paths and temporary file operations."""

    def __init__(self, base_dir: str):
        self._base_dir = Path(base_dir).resolve()

    def get_storage_path(self, storage_key: str) -> Path:
        resolved = (self._base_dir / storage_key).resolve()
        if not resolved.is_relative_to(self._base_dir):
            raise ValueError("Invalid storage key: path traversal detected")
        return resolved

    def create_dataset_context(self, dataset_type: str) -> Tuple[UUID, str, Path]:
        dataset_id = uuid.uuid4()
        storage_key = f"{dataset_type}/{dataset_id}.csv"
        output_path = self.get_storage_path(storage_key)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        return dataset_id, storage_key, output_path

    @staticmethod
    def sanitize_filename(filename: str | None) -> str:
        if not filename:
            return ""
        safe_name = PurePosixPath(filename).name
        return safe_name if safe_name else ""

    @staticmethod
    def save_upload_to_temp(upload_file, suffix: str = "") -> str:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        try:
            shutil.copyfileobj(upload_file.file, tmp)
        finally:
            tmp.close()
        return tmp.name

    @staticmethod
    def cleanup_temp_file(path: str) -> None:
        if os.path.exists(path):
            os.unlink(path)
