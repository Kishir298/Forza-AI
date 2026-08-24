from abc import ABC, abstractmethod
from typing import Optional

from .voice_types import AudioData, TranscriptionResult, SpeakerResult


class AudioInputProvider(ABC):
    @abstractmethod
    def start(self) -> None:
        pass

    @abstractmethod
    def read(self, num_samples: int) -> AudioData:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass


class SpeechRecognizer(ABC):
    @abstractmethod
    def transcribe(self, audio: AudioData) -> TranscriptionResult:
        pass


class SpeakerIdentifier(ABC):
    @abstractmethod
    def identify(self, audio: AudioData) -> SpeakerResult:
        pass


class TextToSpeechProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str) -> AudioData:
        pass


class AudioOutputProvider(ABC):
    @abstractmethod
    def play(self, audio: AudioData) -> None:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass
