"""
Centralized configuration management using pydantic-settings.
All secrets and environment-specific values are loaded from environment variables / .env file.
"""

from typing import List

from pydantic_settings import BaseSettings
from pydantic import field_validator

class Settings(BaseSettings):
    # Database
    database_url: str  

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # CORS
    cors_origins: List[str] = ["http://localhost:5173"]

    # Storage
    storage_dir: str = "local_storage"

    # Ollama / LLM API
    ollama_api_url: str = "http://localhost:11434/api/generate"

    # Server
    debug: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @field_validator("cors_origins")
    @classmethod
    def validate_cors(cls, v, info):
        if v == ["http://localhost:5173"] and not info.data.get("debug"):
            import warnings
            warnings.warn("Using default CORS origins in non-debug mode")
        return v


settings = Settings()
