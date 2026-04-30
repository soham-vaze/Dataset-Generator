"""
Centralized configuration management using pydantic-settings.
All secrets and environment-specific values are loaded from environment variables / .env file.
"""

import os
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://dataset_user:changeme@localhost/dataset_db"

    # JWT
    jwt_secret_key: str = "change-this-to-a-secure-random-key"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # CORS
    cors_origins: List[str] = ["http://localhost:5173"]

    # Storage
    storage_dir: str = "local_storage"

    # Ollama / LLM API
    ollama_api_url: str = "http://10.30.1.34:11434/api/generate"

    # Server
    debug: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
