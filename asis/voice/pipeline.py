"""
Voice pipeline for A.S.I.S.

Coordinates replaceable providers: capture -> transcribe -> identify
speaker -> synthesize -> output. Emits voice events and honors the
``voice`` interruption scope so active speech can be cancelled.
"""

from __future__ import annotations

from asis.events.bus import EventBus
from asis.events.events import Event, EventType
from asis.logging.logger import get_logger
from asis.system.interrupt import InterruptCoordinator

from .models import AudioData, SpeakerResult, TranscriptionResult
from .providers import (
    AudioInputProvider,
    AudioOutputProvider,
    SpeakerIdentifier,
    SpeechRecognizer,
    TextToSpeechProvider,
)

_VOICE_SCOPE = "voice"


class VoicePipeline:
    """Coordinate replaceable voice providers."""

    def __init__(
        self,
        audio_input: AudioInputProvider,
        speech_recognizer: SpeechRecognizer,
        speaker_identifier: SpeakerIdentifier,
        tts: TextToSpeechProvider,
        audio_output: AudioOutputProvider,
        event_bus: EventBus | None = None,
        interrupts: InterruptCoordinator | None = None,
    ) -> None:
        self.audio_input = audio_input
        self.speech_recognizer = speech_recognizer
        self.speaker_identifier = speaker_identifier
        self.tts = tts
        self.audio_output = audio_output
        self.event_bus = event_bus
        self.interrupts = interrupts
        self._logger = get_logger("voice.pipeline")

    def _publish(
        self,
        event_type: EventType,
        **data,
    ) -> None:
        if self.event_bus is None:
            return

        self.event_bus.publish(
            Event(
                type=event_type,
                data=data,
                source="voice",
            )
        )

    def _expects_input(self) -> AudioData:
        if self.interrupts is not None:
            self.interrupts.check(_VOICE_SCOPE)

        audio = self.audio_input.read(1024)
        self._publish(EventType.VOICE_INPUT)

        if self.interrupts is not None:
            self.interrupts.check(_VOICE_SCOPE)

        return audio

    def transcribe(self, audio: AudioData) -> TranscriptionResult:
        """Convert audio into text."""
        self._publish(EventType.VOICE_STT_STARTED)

        result = self.speech_recognizer.transcribe(audio)

        self._publish(
            EventType.VOICE_STT_READY,
            text=result.text,
            language=result.language,
        )

        return result

    def identify_speaker(self, audio: AudioData) -> SpeakerResult:
        """Identify the speaker of the audio."""
        result = self.speaker_identifier.identify(audio)

        self._publish(
            EventType.VOICE_SPEAKER_IDENTIFIED,
            speaker_id=result.speaker_id,
            is_known=result.is_known,
        )

        return result

    def speak(self, text: str) -> AudioData:
        """Synthesize and output speech."""
        self._publish(EventType.VOICE_TTS_STARTED, text=text)

        audio = self.tts.synthesize(text)

        if self.interrupts is not None:
            self.interrupts.check(_VOICE_SCOPE)

        self.audio_output.play(audio)

        self._publish(EventType.VOICE_TTS_FINISHED)
        self._publish(EventType.VOICE_OUTPUT)

        return audio

    def listen_and_transcribe(self) -> TranscriptionResult:
        """Capture a segment and transcribe it."""
        audio = self._expects_input()
        return self.transcribe(audio)

    def stop(self) -> None:
        """Stop active voice operations."""
        self.audio_input.stop()
        self.audio_output.stop()
