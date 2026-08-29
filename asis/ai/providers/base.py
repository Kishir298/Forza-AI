"""
Base interface for A.S.I.S. AI providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator, Sequence

from ..models import AIMessage, AIResponse


class AIProvider(ABC):
    """Interface implemented by every AI backend."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name."""
        raise NotImplementedError

    @property
    @abstractmethod
    def model(self) -> str:
        """Return the active model name."""
        raise NotImplementedError

    @abstractmethod
    def chat(
        self,
        messages: Sequence[AIMessage],
    ) -> AIResponse:
        """Generate a response from a conversation."""
        raise NotImplementedError

    @abstractmethod
    def stream_chat(
        self,
        messages: Sequence[AIMessage],
    ) -> Iterator[str]:
        """Stream a response as text chunks."""
        raise NotImplementedError

    @abstractmethod
    def available(self) -> bool:
        """Return whether the provider is currently available."""
        raise NotImplementedError
