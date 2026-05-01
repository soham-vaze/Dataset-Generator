"""Database initialization script — creates all tables."""

import logging

from infrastructure.db.database import engine
from infrastructure.db.models import Base

logger = logging.getLogger(__name__)


def init_db() -> None:
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error("Failed to initialize database: %s", e)
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
