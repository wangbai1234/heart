"""Stream Session — manages TTS streaming for a turn."""

from __future__ import annotations

import asyncio
import hashlib
from typing import Any, Callable, Optional

import structlog

from heart.ss08_voice.service import VoiceService
from heart.ss08_voice.voice_cache import VoiceCache, should_cache

logger = structlog.get_logger(__name__)


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
    ):
        self._voice = voice_service
        self._send = ws_send_audio
        self._cache = cache
        self._queue: asyncio.Queue[tuple | None] = asyncio.Queue(maxsize=10)
        self._consumer_task: Optional[asyncio.Task] = None
        self._global_seq = 0
        self._cancelled = False
        self._paused = False
        self._current_stream: Any = None
        self._submitted: dict[str, set[str]] = {}  # turn_id -> set of sentence hashes
        self._sentence_seq: dict[str, int] = {}  # turn_id -> monotonic sentence seq
        self._finished: set[str] = set()  # turn_ids that have been finished

    def cancel(self, turn_id: str | None = None) -> None:
        """Cancel the stream session."""
        self._cancelled = True
        if turn_id:
            self._submitted.pop(turn_id, None)
            self._sentence_seq.pop(turn_id, None)
            self._finished.discard(turn_id)
        if self._current_stream is not None:
            try:
                asyncio.ensure_future(self._current_stream.cancel())
            except Exception:
                pass
            self._current_stream = None
        try:
            self._queue.put_nowait(None)
        except Exception:
            pass

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

    async def submit(
        self,
        turn_id: str,
        sentence: str,
        vad: dict | None,
        intimacy: float,
        character_id: str,
        locked_emotion: str | None = None,
        locked_speed_base: float | None = None,
        locked_pitch_base: int | None = None,
    ) -> None:
        """Submit a sentence for TTS synthesis."""
        if self._cancelled:
            return
        if turn_id in self._finished:
            logger.warning("tts_submit_rejected", turn_id=turn_id, reason="finished")
            return
        # Per-turn sentence dedup
        key = hashlib.sha256(sentence.strip().encode()).hexdigest()[:16]
        if key in self._submitted.setdefault(turn_id, set()):
            logger.warning("tts_duplicate_sentence_skipped", turn_id=turn_id, text=sentence[:30])
            return
        self._submitted[turn_id].add(key)
        # Assign monotonic sentence_seq
        sseq = self._sentence_seq.setdefault(turn_id, 0)
        self._sentence_seq[turn_id] = sseq + 1
        logger.info("tts_submit_accepted", turn_id=turn_id, sentence_seq=sseq, text=sentence[:30])
        await self._queue.put(
            (
                turn_id,
                sentence,
                vad,
                intimacy,
                character_id,
                sseq,
                locked_emotion,
                locked_speed_base,
                locked_pitch_base,
            )
        )

    async def start(self) -> None:
        """Start the consumer task."""
        self._consumer_task = asyncio.create_task(self._consume())

    async def finish(self, turn_id: str | None = None) -> None:
        """Signal completion and wait for consumer to finish."""
        if turn_id:
            self._finished.add(turn_id)
            self._submitted.pop(turn_id, None)
            asyncio.get_event_loop().call_later(200, lambda: self._finished.discard(turn_id))
        await self._queue.put(None)
        if self._consumer_task:
            await self._consumer_task

    async def _check_cache(self, req: Any, text: str) -> Optional[bytes]:
        if not self._cache or not should_cache(text):
            return None
        cache_key = VoiceCache.cache_key(req.voice_id, req.emotion, req.speed, req.pitch, text)
        return await self._cache.get(cache_key)

    async def _send_cached_audio(self, turn_id: str, sseq: int, audio: bytes) -> None:
        await self._send(turn_id, sseq, self._global_seq, audio, True)
        self._global_seq += 1

    async def _stream_tts(self, req: Any, turn_id: str, sseq: int) -> list[bytes]:
        audio_chunks = []
        stream = self._voice.provider.stream_synthesize(req)
        self._current_stream = stream

        async for chunk in stream:
            if self._cancelled:
                return audio_chunks
            if chunk.data:
                audio_chunks.append(chunk.data)
                await self._send(turn_id, sseq, self._global_seq, chunk.data, chunk.is_last)
                logger.debug(
                    "audio_send",
                    turn_id=turn_id,
                    sentence_seq=sseq,
                    seq=self._global_seq,
                    is_last=chunk.is_last,
                )
                self._global_seq += 1

        self._current_stream = None
        return audio_chunks

    async def _cache_audio(self, req: Any, text: str, audio_chunks: list[bytes]) -> None:
        if self._cache and should_cache(text) and audio_chunks:
            cache_key = VoiceCache.cache_key(req.voice_id, req.emotion, req.speed, req.pitch, text)
            full_audio = b"".join(audio_chunks)
            await self._cache.set(cache_key, full_audio)

    async def _process_item(self, item: tuple) -> None:
        (
            turn_id,
            text,
            vad,
            intimacy,
            character_id,
            sseq,
            locked_emotion,
            locked_speed_base,
            locked_pitch_base,
        ) = item

        try:
            req = self._voice.director.derive(
                text=text,
                character_id=character_id,
                vad=vad,
                intimacy=intimacy,
                locked_emotion=locked_emotion,
                locked_speed_base=locked_speed_base,
                locked_pitch_base=locked_pitch_base,
            )

            cached_audio = await self._check_cache(req, text)
            if cached_audio:
                await self._send_cached_audio(turn_id, sseq, cached_audio)
                return

            audio_chunks = await self._stream_tts(req, turn_id, sseq)
            await self._cache_audio(req, text, audio_chunks)

        except Exception as e:
            self._current_stream = None
            if not self._cancelled:
                logger.error("tts_stream_failed", error=str(e), text=text[:30] if text else "")

    async def _consume(self) -> None:
        while True:
            while self._paused and not self._cancelled:
                await asyncio.sleep(0.1)

            item = await self._queue.get()
            if item is None or self._cancelled:
                return

            await self._process_item(item)
