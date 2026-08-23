"""
Short-term conversation context for Forza.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContextMessage:
    """A single message in short-term context."""

    role: str
    content: str


class ConversationContext:
    """Bounded in-memory conversation history."""

    def __init__(self, max_messages: int = 20) -> None:
        if max_messages <= 0:
            raise ValueError(
                "max_messages must be greater than zero."
            )

        self.max_messages = max_messages
        self._messages: list[ContextMessage] = []

    def add(self, role: str, content: str) -> None:
        """Add a message to the context."""

        self._messages.append(
            ContextMessage(
                role=role,
                content=content,
            )
        )

        if len(self._messages) > self.max_messages:
            self._messages = self._messages[-self.max_messages :]

    def get(self) -> list[ContextMessage]:
        """Return a copy of the current context."""
        return list(self._messages)

    def clear(self) -> None:
        """Clear the conversation context."""
        self._messages.clear()

    def __len__(self) -> int:
        return len(self._messages)
