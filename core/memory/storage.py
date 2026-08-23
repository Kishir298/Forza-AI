"""
Persistent storage operations for Forza memory.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone

from .database import MemoryDatabase
from .models import Memory, MemoryType


class MemoryStorage:
    """CRUD operations for persistent memories."""

    def __init__(self, database: MemoryDatabase) -> None:
        self.database = database

    def save(self, memory: Memory) -> Memory:
        """Save a memory and return it with its database ID."""

        connection = self.database._connect()

        try:
            cursor = connection.execute(
                """
                INSERT INTO memories (
                    content,
                    memory_type,
                    importance,
                    metadata,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    memory.content,
                    memory.memory_type.value,
                    memory.importance,
                    json.dumps(memory.metadata),
                    memory.created_at.isoformat(),
                    memory.updated_at.isoformat(),
                ),
            )

            connection.commit()
            memory_id = cursor.lastrowid

        finally:
            connection.close()

        return replace(
            memory,
            memory_id=memory_id,
        )

    def get(self, memory_id: int) -> Memory | None:
        """Retrieve a memory by ID."""

        connection = self.database._connect()

        try:
            row = connection.execute(
                """
                SELECT *
                FROM memories
                WHERE id = ?
                """,
                (memory_id,),
            ).fetchone()

        finally:
            connection.close()

        if row is None:
            return None

        return self._row_to_memory(row)

    def delete(self, memory_id: int) -> bool:
        """Delete a memory by ID."""

        connection = self.database._connect()

        try:
            cursor = connection.execute(
                """
                DELETE FROM memories
                WHERE id = ?
                """,
                (memory_id,),
            )

            connection.commit()
            deleted = cursor.rowcount > 0

        finally:
            connection.close()

        return deleted

    def list_all(self) -> list[Memory]:
        """Return all stored memories."""

        connection = self.database._connect()

        try:
            rows = connection.execute(
                """
                SELECT *
                FROM memories
                ORDER BY importance DESC, created_at DESC
                """
            ).fetchall()

        finally:
            connection.close()

        return [
            self._row_to_memory(row)
            for row in rows
        ]

    def search(self, query: str) -> list[Memory]:
        """Perform a basic text search over memory content."""

        query = query.strip()

        if not query:
            return []

        connection = self.database._connect()

        try:
            rows = connection.execute(
                """
                SELECT *
                FROM memories
                WHERE content LIKE ?
                ORDER BY importance DESC, created_at DESC
                """,
                (f"%{query}%",),
            ).fetchall()

        finally:
            connection.close()

        return [
            self._row_to_memory(row)
            for row in rows
        ]

    @staticmethod
    def _row_to_memory(row) -> Memory:
        """Convert a SQLite row into a Memory object."""

        return Memory(
            memory_id=row["id"],
            content=row["content"],
            memory_type=MemoryType(row["memory_type"]),
            importance=row["importance"],
            metadata=json.loads(row["metadata"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )