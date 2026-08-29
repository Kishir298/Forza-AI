"""
Provider interfaces for the A.S.I.S. voice subsystem.

Engines are replaceable so A.S.I.S. runs without hardware or heavy AI
dependencies in tests. Real providers (faster-whisper, TTS engines,
microphone capture) implement these contracts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import AudioData, SpeakerResult, TranscriptionResult


class AudioInputProvider(ABC):
    """Captures audio from a source."""

    @abstractmethod
    def start(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def read(self, num_samples: int) -> AudioData:
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError


class AudioOutputProvider(ABC):
    """Plays audio to an output."""

    @abstractmethod
    def play(self, audio: AudioData) -> None:
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError


class SpeechRecognizer(ABC):
    """Converts audio into text."""

    @abstractmethod
    def transcribe(self, audio: AudioData) -> TranscriptionResult:
        raise NotImplementedError


class SpeakerIdentifier(ABC):
    """Identifies who is speaking."""

    @abstractmethod
    def identify(self, audio: AudioData) -> SpeakerResult:
        raise NotImplementedError


class TextToSpeechProvider(ABC):
    """Converts text into speech audio."""

    @abstractmethod
    def synthesize(self, text: str) -> AudioData:
        raise NotImplementedError
