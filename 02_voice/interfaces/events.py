from enum import Enum


class VoiceEventType(str, Enum):
    SPEECH_STARTED = "speech_started"
    SPEECH_STOPPED = "speech_stopped"
    TRANSCRIPTION_READY = "transcription_ready"
    SPEAKER_IDENTIFIED = "speaker_identified"
    TTS_STARTED = "tts_started"
    TTS_FINISHED = "tts_finished"
    VOICE_ERROR = "voice_error"
