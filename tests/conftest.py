"""Shared fixtures for A.S.I.S. tests."""

from __future__ import annotations

import pytest

from asis.memory import MemoryDatabase, MemoryManager, MemoryStorage


@pytest.fixture()
def memory_manager(tmp_path) -> MemoryManager:
    """A memory manager backed by a temporary SQL file database."""
    database = MemoryDatabase(tmp_path / "memory.db")
    return MemoryManager(MemoryStorage(database))
