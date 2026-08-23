"""
Data models for Forza memory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class MemoryType(StrEnum):
    """Types of information Forza may store."""

    FACT = "fact"
    PREFERENCE = "preference"
    CONTEXT = "context"
    SYSTEM = "system"


@dataclass(frozen=True)
class Memory:
    """A single persistent memory item."""

    content: str
    memory_type: MemoryType = MemoryType.FACT
    importance: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    memory_id: int | None = None

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("Memory content cannot be empty.")

        if not 1 <= self.importance <= 5:
            raise ValueError(
                "Memory importance must be between 1 and 5."
            )
