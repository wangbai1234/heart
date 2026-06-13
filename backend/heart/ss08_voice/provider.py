"""TTS Provider protocol — per runtime_specs/08_voice.md"""

from typing import AsyncGenerator, Protocol

from heart.ss08_voice.types import AudioChunk, TTSRequest, TTSResult


class TTSProvider(Protocol):
    """Protocol for TTS providers (e.g., MiniMax, ElevenLabs)."""

    async def synthesize(self, req: TTSRequest) -> TTSResult:
        """Synthesize speech from text (non-streaming)."""
        ...

    def stream_synthesize(self, req: TTSRequest) -> AsyncGenerator[AudioChunk, None]:
        """Synthesize speech from text (streaming)."""
        ...

    def estimate_cost_cents(self, text: str) -> float:
        """Estimate cost in cents for synthesizing the given text."""
        ...

    @property
    def name(self) -> str:
        """Provider name (e.g., 'minimax', 'elevenlabs')."""
        ...
