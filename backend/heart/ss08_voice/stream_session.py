"""Stream Session — manages TTS streaming for a turn."""

from __future__ import annotations

import re
from typing import Any, Callable, Optional

import structlog

from heart.ss08_voice.service import VoiceService
from heart.ss08_voice.voice_cache import VoiceCache, should_cache

logger = structlog.get_logger(__name__)


# Action-bracket pattern — kept in sync with
# ``heart.ss05_composer.message_splitter._ACTION_RE`` so any bracket the bubble
# splitter treats as an action ("action" kind, grey pill) is also stripped
# from the TTS input. Historically this pattern only recognised parentheses,
# which meant characters emitting 【叹气】 or [回到主题] had their action tags
# read aloud (TEST_REPORT_20260712 §5.4).
_ACTION_PATTERN = re.compile(r"[（(【\[]([^（()【\[\]）)】\n]*)[）)】\]]")


def _extract_tts_stage_directions(text: str) -> tuple[str, list[str]]:
    """Remove action brackets from ``text`` before it hits TTS.

    Keeps the original text intact for transcript/history, but avoids reading
    bracketed descriptions aloud, whether they come as
    （目光停顿片刻，嗓音带着雨后的凉意）, 【叹气】, or [回到主题].
    """
    if not text:
        return "", []
    stripped = text
    directions: list[str] = []
    # Re-run until stable so multiple short bracket segments are removed.
    while True:
        directions.extend(match.group(1).strip() for match in _ACTION_PATTERN.finditer(stripped))
        next_text = _ACTION_PATTERN.sub("", stripped)
        if next_text == stripped:
            break
        stripped = next_text
    stripped = re.sub(r"\s{2,}", " ", stripped)
    stripped = re.sub(r"\n{3,}", "\n\n", stripped)
    return stripped.strip(), [item for item in directions if item]


def _strip_tts_stage_directions(text: str) -> str:
    """Return only the speakable text — every action-bracket span removed."""
    stripped, _ = _extract_tts_stage_directions(text)
    return stripped


class StreamSession:
    """Manages TTS streaming for a single turn.

    Responsible for:
    - Receiving sentence events from orchestrator
    - Running TTS stream synthesis for each sentence
    - Pushing audio chunks to WebSocket
    - Handling cancellation and backpressure
    - Caching short audio clips
    """

    def __init__(
        self,
        voice_service: VoiceService,
        ws_send_audio: Callable[..., Any],
        cache: Optional[VoiceCache] = None,
        preferred_provider_name: Optional[str] = None,
        clone_reference: Optional[str] = None,
    ):
        """Initialize stream session.

        Args:
            voice_service: VoiceService instance.
            ws_send_audio: async callable(turn_id, seq, audio_bytes, is_last)
            cache: Optional VoiceCache for short audio clips.
            preferred_provider_name: The character's configured TTS provider
                (character_voices.voice_provider). Passed to
                synthesize_with_fallback so a Fish-cloned voice renders via Fish
                rather than the process-default primary. None → default chain.
            clone_reference: MiMo zero-shot clone reference handle (the
                character's clone_audio_url). When set, threaded onto the
                TTSRequest so MiMo speaks in the referenced timbre.
        """
        self._voice = voice_service
        self._send = ws_send_audio
        self._cache = cache
        self._preferred_provider_name = preferred_provider_name
        self._clone_reference = clone_reference
        self._global_seq = 0
        self._cancelled = False
        self._paused = False
        self._current_response: Optional[Any] = None
        self.audio_produced = False
        self.tts_provider_name: str = ""
        self.audio_format: str = ""
        self._all_audio_chunks: list[bytes] = []
        # (sentence_text, emotion_label|None) in arrival order. The label is the
        # Layer-3 per-sentence {E:情绪} word parsed upstream; None on text turns.
        self._segments: list[tuple[str, str | None]] = []
        self._last_turn_id: str | None = None
        self._last_character_id: str | None = None
        self._last_vad: dict | None = None
        self._last_intimacy: float = 0.0
        self._last_active_emotions: list[Any] = []

    def cancel(self) -> None:
        """Cancel the stream session."""
        self._cancelled = True
        if self._current_response is not None:
            try:
                self._current_response.aclose()
            except Exception:
                pass
            self._current_response = None

    def pause(self) -> None:
        """Pause the stream session (backpressure)."""
        self._paused = True

    def resume(self) -> None:
        """Resume the stream session."""
        self._paused = False

    @property
    def is_cancelled(self) -> bool:
        """Check if session is cancelled."""
        return self._cancelled

    @property
    def full_audio(self) -> bytes:
        """Accumulated audio as one bytes object, in ``self.audio_format``.

        Note: this is the raw provider payload (e.g. headerless PCM16 for MiMo,
        mp3 for Fish) — callers persisting it must consult ``audio_format`` and
        wrap/label accordingly (see ``_upload_turn_audio``)."""
        if not self._all_audio_chunks:
            return b""
        return b"".join(self._all_audio_chunks)

    async def submit(
        self,
        turn_id: str,
        sentence: str,
        vad: dict | None,
        intimacy: float,
        active_emotions: list[Any] | None,
        character_id: str,
        emotion_label: str | None = None,
    ) -> None:
        """Submit a sentence for TTS synthesis.

        ``emotion_label`` is the Layer-3 per-sentence {E:情绪} word (voice turns
        only); it decorates this sentence individually in :meth:`finish`.
        """
        if self._cancelled:
            return
        cleaned = sentence.strip()
        if not cleaned:
            return
        self._segments.append((cleaned, emotion_label))
        self._last_turn_id = turn_id
        self._last_character_id = character_id
        self._last_vad = vad
        self._last_intimacy = intimacy
        self._last_active_emotions = active_emotions or []

    async def start(self) -> None:
        """Start the session."""
        return None

    async def finish(self) -> None:
        """Synthesize the whole turn once and send a single audio chunk."""
        if self._cancelled:
            return
        full_text = "".join(seg for seg, _ in self._segments).strip()
        if not full_text or not self._last_turn_id or not self._last_character_id:
            return
        tts_text, stage_directions = _extract_tts_stage_directions(full_text)
        tts_text = tts_text or full_text

        # Layer-3: if any sentence carried an {E:情绪} label, bake a per-sentence
        # [中文指令] into the text so Fish S2 varies tone across the turn instead
        # of one flat instruction. derive() then passes the pre-decorated text
        # through (it early-returns when text already opens with '['), while
        # still choosing the turn-level voice_id / speed / pitch.
        baked = self._build_per_sentence_text(full_text)
        if baked is not None:
            tts_text = baked

        req = self._voice.director.derive(
            text=tts_text,
            character_id=self._last_character_id,
            vad=self._last_vad,
            intimacy=self._last_intimacy,
            active_emotions=self._last_active_emotions,
            stage_directions=stage_directions,
        )
        if self._clone_reference:
            # Zero-shot MiMo clone: carry the reference audio handle so the MiMo
            # provider switches to the voiceclone model (TTSRequest is frozen).
            import dataclasses

            req = dataclasses.replace(req, clone_reference=self._clone_reference)
        logger.info(
            "tts_request_prepared",
            character_id=self._last_character_id,
            voice_id=req.voice_id,
            emotion=req.emotion,
            speed=req.speed,
            pitch=req.pitch,
            stage_directions=stage_directions,
            text_preview=req.text[:120],
        )

        cached_audio = await self._check_cache(req, req.text)
        if cached_audio:
            logger.info(
                "tts_cache_hit",
                character_id=self._last_character_id,
                voice_id=req.voice_id,
                emotion=req.emotion,
            )
            self._all_audio_chunks = [cached_audio]
            self.audio_produced = True
            self.audio_format = req.format
            await self._send(self._last_turn_id, self._global_seq, cached_audio, True, req.format)
            self._global_seq += 1
            return

        result = await self._voice.synthesize_with_fallback(
            req, self._last_character_id, self._preferred_provider_name
        )
        if self._cancelled or not result.audio:
            return
        self._all_audio_chunks = [result.audio]
        self.audio_produced = True
        self.tts_provider_name = result.provider_name
        self.audio_format = result.format
        await self._send(
            self._last_turn_id,
            self._global_seq,
            result.audio,
            True,
            result.format,
        )
        self._global_seq += 1
        await self._cache_audio(req, req.text, [result.audio])

    def _build_per_sentence_text(self, fallback: str) -> Optional[str]:
        """Inline a Fish S2 [中文指令] before each labelled sentence.

        Returns the decorated whole-turn text, or None to signal "no per-sentence
        labels apply — use the existing whole-turn derive() path". None is
        returned when: no segment carried a label, the director isn't in S2
        mode, or the voice is a clone (clone_stability voices suppress
        model-level emotion prefixes to protect timbre — Layer 2 handles them).
        """
        if not any(label for _, label in self._segments):
            return None
        director = self._voice.director
        if getattr(director, "emotion_mode", "s2") != "s2":
            return None
        try:
            from heart.ss08_voice.voice_catalog import get_voice_profile

            profile = get_voice_profile(self._last_character_id or "")
            if profile.clone_stability:
                return None
        except Exception:
            # No profile / lookup failure → fall back to whole-turn path.
            return None

        pieces: list[str] = []
        for sentence, label in self._segments:
            spoken = _strip_tts_stage_directions(sentence).strip()
            if not spoken:
                continue
            instr = director.resolve_s2_instruction(label) if label else ""
            pieces.append(f"{instr}{spoken}" if instr else spoken)
        baked = "".join(pieces).strip()
        return baked or fallback

    async def _check_cache(self, req: Any, text: str) -> Optional[bytes]:
        """Check cache for audio."""
        if not self._cache or not should_cache(text):
            return None
        cache_key = VoiceCache.cache_key(req.voice_id, req.emotion, req.speed, req.pitch, text)
        return await self._cache.get(cache_key)

    async def _cache_audio(self, req: Any, text: str, audio_chunks: list[bytes]) -> None:
        """Cache audio if conditions are met."""
        if self._cache and should_cache(text) and audio_chunks:
            cache_key = VoiceCache.cache_key(req.voice_id, req.emotion, req.speed, req.pitch, text)
            full_audio = b"".join(audio_chunks)
            await self._cache.set(cache_key, full_audio)
