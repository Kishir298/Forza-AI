"""
Data models for the A.S.I.S. AI subsystem.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class MessageRole(StrEnum):
    """Standard conversational roles used with AI models."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True)
class AIMessage:
    """A message sent to or returned by an AI model."""

    role: MessageRole
    content: str

    def __post_init__(self) -> None:
        if not isinstance(self.role, MessageRole):
            raise TypeError(f"Invalid message role: {self.role!r}.")

        if not isinstance(self.content, str):
            raise TypeError(
                f"Message content must be str, got {type(self.content).__name__}."
            )


@dataclass(frozen=True)
class AIResponse:
    """Standard response returned by an AI provider."""

    content: str
    model: str
    provider: str
    metadata: dict[str, Any] = field(default_factory=dict)
