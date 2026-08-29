"""
Data models for the A.S.I.S. voice subsystem.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AudioData:
    """A captured or synthesized audio segment."""

    samples: Any
    sample_rate: int = 16_000
    channels: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TranscriptionResult:
    """Result returned by a speech-to-text engine."""

    text: str
    language: str | None = None
    confidence: float | None = None
    duration: float | None = None


@dataclass(frozen=True)
class SpeakerResult:
    """Result returned by a speaker identification engine."""

    speaker_id: str
    confidence: float | None = None
    is_known: bool = False
