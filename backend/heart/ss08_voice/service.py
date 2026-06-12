"""Voice Service — per runtime_specs/08_voice.md"""

import structlog

from heart.ss08_voice.provider import TTSProvider
from heart.ss08_voice.types import TTSRequest, TTSResult
from heart.ss08_voice.voice_catalog import get_voice_id

logger = structlog.get_logger(__name__)


class VoiceService:
    """Service for synthesizing speech with character-specific voices."""

    def __init__(self, provider: TTSProvider):
        self._provider = provider

    async def synthesize_for_character(
        self,
        text: str,
        character_id: str,
        emotion: str = "neutral",
        **overrides,
    ) -> TTSResult:
        """Synthesize speech for a specific character.

        Args:
            text: Text to synthesize.
            character_id: Character ID (e.g., 'rin', 'dorothy').
            emotion: Emotion to apply (happy, sad, angry, etc.).
            **overrides: Additional TTSRequest parameters (speed, pitch, etc.).
        """
        voice_id = get_voice_id(character_id)
        return await self._provider.synthesize(
            TTSRequest(
                text=text,
                voice_id=voice_id,
                emotion=emotion,
                **overrides,
            )
        )
