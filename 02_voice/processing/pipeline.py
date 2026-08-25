from __future__ import annotations

from ..interfaces.providers import (
    AudioInputProvider,
    AudioOutputProvider,
    SpeakerIdentifier,
    SpeechRecognizer,
    TextToSpeechProvider,
)
from ..interfaces.voice_types import (
    AudioData,
    SpeakerResult,
    TranscriptionResult,
)


class VoicePipeline:
    """Coordinate replaceable voice providers."""

    def __init__(
        self,
        audio_input: AudioInputProvider,
        speech_recognizer: SpeechRecognizer,
        speaker_identifier: SpeakerIdentifier,
        tts: TextToSpeechProvider,
        audio_output: AudioOutputProvider,
    ) -> None:
        self.audio_input = audio_input
        self.speech_recognizer = speech_recognizer
        self.speaker_identifier = speaker_identifier
        self.tts = tts
        self.audio_output = audio_output

    def transcribe(self, audio: AudioData) -> TranscriptionResult:
        return self.speech_recognizer.transcribe(audio)

    def identify_speaker(self, audio: AudioData) -> SpeakerResult:
        return self.speaker_identifier.identify(audio)

    def speak(self, text: str) -> None:
        audio = self.tts.synthesize(text)
        self.audio_output.play(audio)

    def stop(self) -> None:
        self.audio_input.stop()
        self.audio_output.stop()
