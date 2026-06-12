"""Voice Service — per runtime_specs/08_voice.md"""

from __future__ import annotations

from typing import Dict, List, Optional

import structlog

from heart.ss08_voice.provider import TTSProvider
from heart.ss08_voice.types import TTSRequest, TTSResult
from heart.ss08_voice.voice_catalog import get_voice_id
from heart.ss08_voice.voice_director import VoiceDirector

logger = structlog.get_logger(__name__)


class VoiceService:
    """Service for synthesizing speech with character-specific voices."""

    def __init__(self, provider: TTSProvider, director: Optional[VoiceDirector] = None):
        self._provider = provider
        self._director = director or VoiceDirector()

    @property
    def director(self) -> VoiceDirector:
        """Expose director for external use (e.g., StreamSession)."""
        return self._director

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

    async def synthesize_with_state(
        self,
        text: str,
        character_id: str,
        vad: Optional[Dict[str, float]] = None,
        intimacy: float = 0.0,
        active_emotions: Optional[List[str]] = None,
    ) -> TTSResult:
        """Synthesize speech with emotion/relationship state.

        Args:
            text: Text to synthesize.
            character_id: Character ID (e.g., 'rin', 'dorothy').
            vad: VAD dict with valence, arousal, dominance (-1..1).
            intimacy: Intimacy level (0..1).
            active_emotions: List of active emotion names.
        """
        req = self._director.derive(text, character_id, vad, intimacy, active_emotions)
        return await self._provider.synthesize(req)
