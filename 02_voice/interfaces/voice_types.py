from dataclasses import dataclass
from typing import Optional


@dataclass
class AudioData:
    samples: object
    sample_rate: int
    channels: int = 1


@dataclass
class TranscriptionResult:
    text: str
    language: Optional[str] = None
    confidence: Optional[float] = None
    duration: Optional[float] = None


@dataclass
class SpeakerResult:
    speaker_id: Optional[str]
    confidence: Optional[float] = None
    is_known: bool = False


@dataclass
class VoiceEvent:
    event_type: str
    data: object = None
