"""Backward compatibility - use infrastructure.db.database instead."""

from infrastructure.db.database import Base, SessionLocal, engine, get_db

__all__ = ["Base", "SessionLocal", "engine", "get_db"]
