from abc import ABC, abstractmethod

from .voice_types import AudioData, TranscriptionResult, SpeakerResult


class VoiceSystem(ABC):
    """Interface between the Forza voice subsystem and the rest of Forza."""

    @abstractmethod
    def listen(self) -> AudioData:
        """Capture audio from the user."""
        pass

    @abstractmethod
    def transcribe(self, audio: AudioData) -> TranscriptionResult:
        """Convert audio into text."""
        pass

    @abstractmethod
    def identify_speaker(self, audio: AudioData) -> SpeakerResult:
        """Identify the speaker."""
        pass

    @abstractmethod
    def speak(self, text: str) -> None:
        """Convert text to speech and output it."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop active voice operations."""
        pass
