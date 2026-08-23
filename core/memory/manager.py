"""
High-level memory manager for Forza.
"""

from __future__ import annotations

from typing import Any

from core.logging.logger import get_logger

from .models import Memory, MemoryType
from .storage import MemoryStorage


class MemoryManager:
    """High-level interface for Forza persistent memory."""

    def __init__(self, storage: MemoryStorage) -> None:
        self.storage = storage
        self.logger = get_logger("memory")

    def remember(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.FACT,
        importance: int = 1,
        metadata: dict[str, Any] | None = None,
    ) -> Memory:
        """Create and persist a new memory."""

        memory = Memory(
            content=content,
            memory_type=memory_type,
            importance=importance,
            metadata=metadata or {},
        )

        saved = self.storage.save(memory)

        self.logger.info(
            "Memory saved: %s",
            saved.memory_id,
        )

        return saved

    def recall(self, memory_id: int) -> Memory | None:
        """Retrieve one memory."""
        return self.storage.get(memory_id)

    def forget(self, memory_id: int) -> bool:
        """Delete one memory."""
        deleted = self.storage.delete(memory_id)

        if deleted:
            self.logger.info(
                "Memory deleted: %s",
                memory_id,
            )

        return deleted

    def search(self, query: str) -> list[Memory]:
        """Search stored memories."""
        return self.storage.search(query)

    def all_memories(self) -> list[Memory]:
        """Return all memories."""
        return self.storage.list_all()
