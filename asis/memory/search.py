"""
Memory search interface for A.S.I.S.
"""

from __future__ import annotations

from .models import Memory, MemoryCategory
from .storage import MemoryStorage


class MemorySearch:
    """Search interface for persistent memory."""

    def __init__(self, storage: MemoryStorage) -> None:
        self.storage = storage

    def text(
        self,
        query: str,
        category: MemoryCategory | None = None,
    ) -> list[Memory]:
        """Search memory using text matching."""
        return self.storage.search(query, category=category)
