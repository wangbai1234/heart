"""Stream Session — manages TTS streaming for a turn."""

from __future__ import annotations

import asyncio
import contextlib
import re
from typing import Any, Callable, Optional

import structlog

from heart.ss08_voice.service import VoiceService
from heart.ss08_voice.voice_cache import VoiceCache, should_cache

logger = structlog.get_logger(__name__)

# Sentinel enqueued by finish() to tell the synth worker no more sentences are
# coming, so it can drain and exit.
_FINISH = object()

# Ceiling for draining queued sentences after finish() — bounds a stuck provider
# so finish() can't hang the turn. The turn-level timeout is the outer backstop.
_DRAIN_TIMEOUT_S = 40.0


# Action-bracket pattern — strips the action/narration namespace
# （）/()/【】 from the TTS input so 【叹气】-style tags aren't read aloud
# (TEST_REPORT_20260712 §5.4). Half-width [] is DELIBERATELY excluded: Layer-3
# reserves [中文指令] as the Fish S2 instruction namespace, which must survive
# to the provider (voice turns strip [] from the *display* path separately, via
# emotion_sentinel.InstructionStripper). Actions therefore use （）/【】 only.
_ACTION_PATTERN = re.compile(r"[（(【]([^（()【【\]）)】\n]*)[）)】]")


def _extract_tts_stage_directions(text: str) -> tuple[str, list[str]]:
    """Remove the （）/【】 action namespace from ``text`` before it hits TTS.

    Keeps the original text intact for transcript/history, but avoids reading
    bracketed descriptions aloud, e.g. （目光停顿片刻，嗓音带着雨后的凉意）or
    【叹气】. Half-width [中文指令] is left in place on purpose — it is the Fish
    S2 instruction namespace and must reach the provider.
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
        # Sentence-level pipeline: submit() enqueues one job per sentence; a
        # background worker (started in start()) synthesizes them in arrival
        # order and streams each sentence's audio to the client the moment it's
        # ready — so the character starts speaking sentence 1 while the LLM is
        # still emitting sentence 3. finish() enqueues _FINISH and awaits drain.
        self._queue: asyncio.Queue[Any] = asyncio.Queue()
        self._worker: Optional[asyncio.Task] = None

    def cancel(self) -> None:
        """Cancel the stream session."""
        self._cancelled = True
        if self._worker is not None and not self._worker.done():
            self._worker.cancel()
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

    async def start(self) -> None:
        """Start the background synth worker so submit() streams per sentence."""
        if self._worker is None:
            self._worker = asyncio.create_task(self._run_worker())

    async def submit(
        self,
        turn_id: str,
        sentence: str,
        vad: dict | None,
        intimacy: float,
        active_emotions: list[Any] | None,
        character_id: str,
    ) -> None:
        """Enqueue one sentence for TTS synthesis (non-blocking).

        The worker synthesizes queued sentences in arrival order and streams
        each sentence's audio the instant it's ready, so playback of sentence 1
        overlaps synthesis of later sentences. Layer-3 emotion rides inline as a
        leading ``[中文指令]`` the LLM emits at the sentence head; it is preserved
        verbatim through the TTS path (only the （）/【】 action namespace is
        stripped) so Fish S2 varies tone per sentence with no backend decoration.
        """
        if self._cancelled:
            return
        cleaned = sentence.strip()
        if not cleaned:
            return
        # Defensive: production always calls start() first, but a caller that
        # skips it must still stream (and finish() must have a worker to drain).
        if self._worker is None:
            self._worker = asyncio.create_task(self._run_worker())
        self._queue.put_nowait(
            {
                "turn_id": turn_id,
                "sentence": cleaned,
                "vad": vad,
                "intimacy": intimacy,
                "active_emotions": active_emotions or [],
                "character_id": character_id,
            }
        )

    async def finish(self) -> None:
        """Signal end-of-sentences and wait for the worker to drain the queue.

        A lazily-started worker is normal (start() runs before any submit), but
        guard for the degenerate no-audio turn where finish() is reached without
        start() ever having run.
        """
        if self._cancelled:
            return
        if self._worker is None:
            return
        self._queue.put_nowait(_FINISH)
        with contextlib.suppress(asyncio.TimeoutError, asyncio.CancelledError):
            await asyncio.wait_for(asyncio.shield(self._worker), timeout=_DRAIN_TIMEOUT_S)

    async def _run_worker(self) -> None:
        """Drain the sentence queue, synthesizing + streaming each in order."""
        while True:
            job = await self._queue.get()
            if job is _FINISH:
                return
            if self._cancelled:
                continue  # drain to _FINISH without synthesizing
            while self._paused and not self._cancelled:
                await asyncio.sleep(0.05)
            try:
                await self._synthesize_one(job)
            except Exception:
                # One sentence failing must not kill the turn — whatever already
                # streamed still plays; the turn terminates normally upstream.
                logger.exception(
                    "tts_sentence_synth_failed",
                    character_id=job.get("character_id"),
                    text_preview=str(job.get("sentence"))[:80],
                )

    async def _synthesize_one(self, job: dict) -> None:
        """Synthesize a single sentence and stream its audio to the client."""
        turn_id = job["turn_id"]
        character_id = job["character_id"]
        tts_text, stage_directions = _extract_tts_stage_directions(job["sentence"])
        tts_text = tts_text or job["sentence"]

        req = self._voice.director.derive(
            text=tts_text,
            character_id=character_id,
            vad=job["vad"],
            intimacy=job["intimacy"],
            active_emotions=job["active_emotions"],
            stage_directions=stage_directions,
        )
        if self._clone_reference:
            # Zero-shot MiMo clone: carry the reference audio handle so the MiMo
            # provider switches to the voiceclone model (TTSRequest is frozen).
            import dataclasses

            req = dataclasses.replace(req, clone_reference=self._clone_reference)

        cached_audio = await self._check_cache(req, req.text)
        if cached_audio:
            logger.info(
                "tts_cache_hit",
                character_id=character_id,
                voice_id=req.voice_id,
                emotion=req.emotion,
            )
            await self._emit(turn_id, cached_audio, req.format, "cache")
            return

        result = await self._voice.synthesize_with_fallback(
            req, character_id, self._preferred_provider_name
        )
        if self._cancelled or not result.audio:
            return
        self.tts_provider_name = result.provider_name
        await self._emit(turn_id, result.audio, result.format, result.provider_name)
        await self._cache_audio(req, req.text, [result.audio])

    async def _emit(self, turn_id: str, audio: bytes, fmt: str, source: str) -> None:
        """Stream one sentence's audio chunk and accumulate it for persistence.

        is_last stays False on every chunk — the turn's terminal signal is the
        WS ``turn_end`` frame (the client finalizes on that, not on is_last),
        so mid-turn sentence chunks must not claim to be last.
        """
        if self._cancelled:
            return
        self._all_audio_chunks.append(audio)
        self.audio_produced = True
        self.audio_format = fmt
        await self._send(turn_id, self._global_seq, audio, False, fmt)
        self._global_seq += 1

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
