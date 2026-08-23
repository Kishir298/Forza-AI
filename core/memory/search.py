"""
Memory search interface.
"""

from __future__ import annotations

from .models import Memory
from .storage import MemoryStorage


class MemorySearch:
    """Search interface for persistent memory."""

    def __init__(self, storage: MemoryStorage) -> None:
        self.storage = storage

    def text(self, query: str) -> list[Memory]:
        """Search memory using text matching."""
        return self.storage.search(query)
