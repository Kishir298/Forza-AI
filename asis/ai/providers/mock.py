"""
Deterministic in-memory AI provider for A.S.I.S.

Used by tests and as a zero-dependency fallback when no AI backend is
available. Responses are configurable so behavior can be scripted.
"""

from __future__ import annotations

import time
from collections.abc import Iterable, Sequence

from ..models import AIMessage, AIResponse
from .base import AIProvider


class MockAIProvider(AIProvider):
    """Scriptable AI provider that never touches the network."""

    def __init__(
        self,
        model: str = "mock",
        responses: Iterable[str] = ("This is a mock response.",),
        *,
        fail: bool = False,
        delay: float = 0.0,
        metadata: dict | None = None,
    ) -> None:
        self._model = model
        self._pool = list(responses)
        self.fail = fail
        self.delay = delay
        self.metadata = metadata or {}
        self._index = 0

    @property
    def name(self) -> str:
        return "mock"

    @property
    def model(self) -> str:
        return self._model

    def available(self) -> bool:
        return not self.fail

    def _next_response(self) -> str:
        if not self._pool:
            return ""

        response = self._pool[self._index % len(self._pool)]
        self._index += 1
        return response

    def chat(
        self,
        messages: Sequence[AIMessage],
    ) -> AIResponse:
        if self.fail:
            raise ConnectionError("Mock AI provider is configured to fail.")

        if self.delay:
            time.sleep(self.delay)

        return AIResponse(
            content=self._next_response(),
            model=self._model,
            provider=self.name,
            metadata={"mock": True, **self.metadata},
        )

    def stream_chat(
        self,
        messages: Sequence[AIMessage],
    ) -> Iterable[str]:
        if self.fail:
            raise ConnectionError("Mock AI provider is configured to fail.")

        if self.delay:
            time.sleep(self.delay)

        content = self._next_response()

        for word in content.split(" "):
            yield word + " "
