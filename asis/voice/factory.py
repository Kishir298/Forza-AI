"""
Voice component factory for A.S.I.S.

Builds the configured set of voice engines. When a selected engine is
unavailable (missing hardware or optional dependencies), a helpful
error is raised instead of silently failing.
"""

from __future__ import annotations

from asis.configuration.settings import settings
from asis.errors import VoiceError
from asis.logging.logger import get_logger

from .engines.mock import (
    MockAudioInput,
    MockAudioOutput,
    MockSpeakerIdentifier,
    MockSpeechRecognizer,
    MockTextToSpeech,
)
from .models import AudioData
from .providers import (
    AudioInputProvider,
    AudioOutputProvider,
    SpeakerIdentifier,
    SpeechRecognizer,
    TextToSpeechProvider,
)


def _unsupported(engine: str, kind: str):
    return VoiceError(
        f"The '{engine}' {kind} engine is not provided yet. "
        f"Install the voice extras and implement the provider, or "
        f"set ASIS_VOICE_{kind.upper()}_ENGINE=mock."
    )


def create_speech_recognizer() -> SpeechRecognizer:
    """Build the configured speech recognition engine."""
    engine = settings.voice.stt.engine.lower()

    if engine in {"mock", ""}:
        return MockSpeechRecognizer(
            language=settings.voice.stt.language or None,
        )

    raise _unsupported(engine, "stt")


def create_speaker_identifier() -> SpeakerIdentifier:
    """Build the configured speaker identification engine."""
    engine = settings.voice.speaker.engine.lower()

    if engine in {"mock", ""}:
        return MockSpeakerIdentifier(
            confidence=settings.voice.speaker.confidence,
        )

    raise _unsupported(engine, "speaker")


def create_tts() -> TextToSpeechProvider:
    """Build the configured text-to-speech engine."""
    engine = settings.voice.tts.engine.lower()

    if engine in {"mock", ""}:
        return MockTextToSpeech(
            sample_rate=settings.voice.sample_rate,
        )

    raise _unsupported(engine, "tts")


def create_audio_input(segments: list[AudioData] | None = None) -> AudioInputProvider:
    """Build the configured audio input engine."""
    return MockAudioInput(segments or [])


def create_audio_output() -> AudioOutputProvider:
    """Build the configured audio output engine."""
    return MockAudioOutput()


def create_voice_engines() -> dict:
    """Build every voice engine from the current settings."""
    logger = get_logger("voice.factory")

    engines = {
        "audio_input": create_audio_input(),
        "speech_recognizer": create_speech_recognizer(),
        "speaker_identifier": create_speaker_identifier(),
        "tts": create_tts(),
        "audio_output": create_audio_output(),
    }

    for kind, engine in engines.items():
        logger.debug("Voice engine: %s -> %s", kind, type(engine).__name__)

    return engines
