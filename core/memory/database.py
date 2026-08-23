"""
SQLite database layer for Forza memory.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


class MemoryDatabase:
    """SQLite database used by the memory subsystem."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        """Create a database connection."""
        connection = sqlite3.connect(
            self.database_path,
            timeout=10,
        )

        connection.row_factory = sqlite3.Row

        return connection

    def _initialize(self) -> None:
        """Create required database tables."""

        connection = self._connect()

        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    importance INTEGER NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_memories_type
                ON memories(memory_type)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_memories_importance
                ON memories(importance)
                """
            )

            connection.commit()

        finally:
            connection.close()