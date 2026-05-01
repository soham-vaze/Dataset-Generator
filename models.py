"""Backward compatibility - use infrastructure.db.models instead."""

from infrastructure.db.models import Dataset, User

__all__ = ["Dataset", "User"]
