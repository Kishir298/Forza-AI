"""
Configuration-driven A.S.I.S. identity.

The identity (name, personality, preferences) lives here and is loaded
from configuration, never scattered through the inference engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from asis.configuration.settings import settings
from asis.errors import ConfigurationError

from .personality import DEFAULT_PERSONALITY


@dataclass(frozen=True)
class Identity:
    """The identity presented by A.S.I.S. during conversations."""

    name: str
    title: str
    personality: str
    preferences: dict[str, Any] = field(default_factory=dict)
    greeting: str = ""

    def system_prompt(self) -> str:
        """Build the base system prompt from this identity."""
        return f"You are {self.name}, {self.title}.\n\n{self.personality}"


def build_identity(
    personality_text: str | None = None,
    preferences: dict[str, Any] | None = None,
) -> Identity:
    """Build an Identity from configuration and optional overrides."""
    text = personality_text or DEFAULT_PERSONALITY

    try:
        rendered = text.format(
            name=settings.identity.name,
            title=settings.identity.title,
        )
    except (KeyError, ValueError) as exc:
        raise ConfigurationError(f"Invalid personality template: {exc}") from exc

    return Identity(
        name=settings.identity.name,
        title=settings.identity.title,
        personality=rendered,
        preferences=preferences or {},
        greeting=f"Yo, wassup? Running as {settings.identity.name}.",
    )
