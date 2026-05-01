"""Backward compatibility - use infrastructure.db.database_init instead."""

import logging

from infrastructure.db.database_init import init_db

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
