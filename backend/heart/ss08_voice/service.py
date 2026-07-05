"""Voice Service — per runtime_specs/08_voice.md"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import structlog

from heart.ss08_voice.provider import TTSProvider
from heart.ss08_voice.types import TTSRequest, TTSResult
from heart.ss08_voice.voice_catalog import get_voice_id
from heart.ss08_voice.voice_director import VoiceDirector

logger = structlog.get_logger(__name__)


class VoiceService:
    """Service for synthesizing speech with character-specific voices.

    Supports dual-provider architecture: primary TTS + optional fallback.
    """

    def __init__(
        self,
        provider: TTSProvider,
        fallback: Optional[TTSProvider] = None,
        director: Optional[VoiceDirector] = None,
    ):
        self._provider = provider
        self._fallback = fallback
        self._director = director or VoiceDirector()

    @property
    def director(self) -> VoiceDirector:
        """Expose director for external use (e.g., StreamSession)."""
        return self._director

    @property
    def provider(self) -> TTSProvider:
        """Expose provider for external use (e.g., StreamSession)."""
        return self._provider

    @property
    def fallback_provider(self) -> Optional[TTSProvider]:
        """Expose fallback provider (e.g., for StreamSession)."""
        return self._fallback

    async def _synthesize_with_provider(
        self, provider: TTSProvider, req: TTSRequest, character_id: str = "rin"
    ) -> TTSResult:
        """Dispatch synthesis to a provider, handling character_id for MiMo."""
        logger.info(
            "tts_provider_request",
            provider=provider.name,
            character_id=character_id,
            voice_id=req.voice_id,
            emotion=req.emotion,
            speed=req.speed,
            pitch=req.pitch,
            text_preview=req.text[:80],
        )
        if provider.name == "mimo":
            return await provider.synthesize(req, character_id)  # type: ignore[call-arg]
        return await provider.synthesize(req)

    async def synthesize_with_fallback(
        self, req: TTSRequest, character_id: str = "rin"
    ) -> TTSResult:
        """Synthesize with primary provider, falling back on failure."""
        try:
            result = await self._synthesize_with_provider(self._provider, req, character_id)
            logger.info(
                "tts_provider_success",
                provider=self._provider.name,
                character_id=character_id,
                voice_id=req.voice_id,
                request_id=result.request_id,
                duration_ms=result.duration_ms,
            )
            return result
        except Exception as e:
            logger.warning(
                "primary_tts_failed",
                provider=self._provider.name,
                character_id=character_id,
                voice_id=req.voice_id,
                error=str(e),
            )
            if self._fallback:
                logger.info("tts_fallback_to", provider=self._fallback.name)
                result = await self._synthesize_with_provider(self._fallback, req, character_id)
                logger.info(
                    "tts_provider_success",
                    provider=self._fallback.name,
                    character_id=character_id,
                    voice_id=req.voice_id,
                    request_id=result.request_id,
                    duration_ms=result.duration_ms,
                    via_fallback=True,
                )
                return result
            raise

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
        req = TTSRequest(
            text=text,
            voice_id=voice_id,
            emotion=emotion,
            **overrides,
        )
        return await self.synthesize_with_fallback(req, character_id)

    async def synthesize_with_state(
        self,
        text: str,
        character_id: str,
        vad: Optional[Dict[str, float]] = None,
        intimacy: float = 0.0,
        active_emotions: Optional[List[Any]] = None,
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
        return await self.synthesize_with_fallback(req, character_id)
