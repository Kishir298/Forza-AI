"""
Ollama AI provider for Forza.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import requests

from .models import AIMessage, AIResponse
from .provider import AIProvider


class OllamaProvider(AIProvider):
    """AI provider backed by a local Ollama server."""

    def __init__(
        self,
        model: str = "qwen2.5:3b",
        host: str = "http://127.0.0.1:11434",
        timeout: float = 120.0,
    ) -> None:
        self._model = model
        self.host = host.rstrip("/")
        self.timeout = timeout

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def model(self) -> str:
        return self._model

    def available(self) -> bool:
        """Check whether Ollama is reachable."""

        try:
            response = requests.get(
                f"{self.host}/api/tags",
                timeout=5,
            )

            return response.ok

        except requests.RequestException:
            return False

    def chat(
        self,
        messages: Sequence[AIMessage],
    ) -> AIResponse:
        """Send a conversation to Ollama."""

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {
                    "role": message.role,
                    "content": message.content,
                }
                for message in messages
            ],
            "stream": False,
        }

        try:
            response = requests.post(
                f"{self.host}/api/chat",
                json=payload,
                timeout=self.timeout,
            )

            response.raise_for_status()

        except requests.RequestException as exc:
            raise RuntimeError(
                f"Could not communicate with Ollama: {exc}"
            ) from exc

        data = response.json()

        message = data.get("message", {})

        content = message.get("content")

        if not isinstance(content, str):
            raise RuntimeError(
                "Ollama returned an invalid response."
            )

        return AIResponse(
            content=content,
            model=self._model,
            provider=self.name,
            metadata={
                "done": data.get("done"),
                "total_duration": data.get("total_duration"),
                "prompt_eval_count": data.get("prompt_eval_count"),
                "eval_count": data.get("eval_count"),
            },
        )