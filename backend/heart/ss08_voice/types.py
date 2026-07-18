"""Voice subsystem types — per runtime_specs/08_voice.md"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TTSRequest:
    """Request to synthesize speech from text."""

    text: str
    voice_id: str
    emotion: str = "neutral"  # happy/sad/angry/fearful/disgusted/surprised/neutral
    speed: float = 1.0  # 0.5-2.0
    pitch: int = 0  # -12..12 semitones
    volume: float = 1.0  # 0-2
    format: str = "mp3"  # mp3/pcm
    sample_rate: int = 24000


@dataclass(frozen=True)
class AudioChunk:
    """A chunk of audio data in a stream."""

    seq: int
    data: bytes
    format: str
    is_last: bool = False


@dataclass(frozen=True)
class TTSResult:
    """Result of a TTS synthesis request."""

    audio: bytes
    format: str
    duration_ms: int
    request_id: str
    provider_name: str = ""
