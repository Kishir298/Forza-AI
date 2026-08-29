"""
High-level memory manager for A.S.I.S.

Provides CRUD plus the formatted memory context used by the prompt
assembler. Cloud persistence is not performed here; that is R.E.S.C.S.'
responsibility once wired.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from asis.events.bus import EventBus
from asis.events.events import Event, EventType
from asis.logging.logger import get_logger

from .models import Memory, MemoryCategory, MemoryType
from .storage import MemoryStorage

_MEMORY_RULES = (
    "MEMORY RULES:\n"
    "- User memories describe the user.\n"
    "- Identity memories describe A.S.I.S.\n"
    "- Use these memories when relevant.\n"
    "- Never invent memories.\n"
    "- Never claim to remember something that is not shown.\n"
    "- Do not mention the memory system unless asked."
)


class MemoryManager:
    """High-level interface for A.S.I.S. persistent memory."""

    def __init__(
        self,
        storage: MemoryStorage,
        event_bus: EventBus | None = None,
    ) -> None:
        self.storage = storage
        self.event_bus = event_bus
        self.logger = get_logger("memory")

    def _publish(
        self,
        event_type: EventType,
        **data,
    ) -> None:
        if self.event_bus is None:
            return

        self.event_bus.publish(
            Event(
                type=event_type,
                data=data,
                source="memory",
            )
        )

    def remember(
        self,
        content: str,
        category: MemoryCategory = MemoryCategory.GENERAL,
        memory_type: MemoryType = MemoryType.FACT,
        importance: int = 5,
        metadata: dict[str, Any] | None = None,
    ) -> Memory:
        """Create and persist a new memory."""
        memory = Memory(
            content=content,
            category=category,
            memory_type=memory_type,
            importance=importance,
            metadata=metadata or {},
        )

        saved = self.storage.save(memory)

        self.logger.info("Memory saved: %s", saved.memory_id)
        self._publish(EventType.MEMORY_SAVED, memory_id=saved.memory_id)

        return saved

    def recall(self, memory_id: int) -> Memory | None:
        """Retrieve one memory."""
        return self.storage.get(memory_id)

    def update(self, memory: Memory) -> Memory | None:
        """Update an existing memory."""
        return self.storage.update(memory)

    def forget(self, memory_id: int) -> bool:
        """Delete one memory."""
        deleted = self.storage.delete(memory_id)

        if deleted:
            self.logger.info("Memory deleted: %s", memory_id)
            self._publish(EventType.MEMORY_DELETED, memory_id=memory_id)

        return deleted

    def clear(self) -> int:
        """Delete every stored memory."""
        count = self.storage.clear()

        if count:
            self.logger.info("Memory cleared: %d items", count)
            self._publish(EventType.MEMORY_CLEARED, count=count)

        return count

    def search(
        self,
        query: str,
        category: MemoryCategory | None = None,
    ) -> list[Memory]:
        """Search stored memories."""
        return self.storage.search(query, category=category)

    def all_memories(
        self,
        category: MemoryCategory | None = None,
    ) -> list[Memory]:
        """Return every stored memory."""
        return self.storage.list_all(category=category)

    def with_importance(self, memory: Memory, importance: int) -> Memory:
        """Return a copy of a memory with a new importance."""
        return replace(memory, importance=importance)

    def build_memory_context(self) -> str:
        """Build the long-term memory section for the system prompt."""
        by_category = {
            category: self.storage.list_all(category=category)
            for category in MemoryCategory
        }

        lines: list[str] = ["LONG-TERM MEMORY:"]

        for category, memories in by_category.items():
            lines.extend(["", f"{category.value.upper()} MEMORIES:"])

            if memories:
                lines.extend(f"- {item.content}" for item in memories)
            else:
                lines.append("- None.")

        lines.extend(["", *_MEMORY_RULES.splitlines()])

        return "\n".join(lines)
