"""Stream Session — manages TTS streaming for a turn."""

from __future__ import annotations

import asyncio
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
        """Initialize stream session.

        Args:
            voice_service: VoiceService instance.
            ws_send_audio: async callable(turn_id, seq, audio_bytes, is_last)
            cache: Optional VoiceCache for short audio clips.
        """
        self._voice = voice_service
        self._send = ws_send_audio
        self._cache = cache
        self._queue: asyncio.Queue[tuple | None] = asyncio.Queue(maxsize=10)
        self._consumer_task: Optional[asyncio.Task] = None
        self._global_seq = 0
        self._cancelled = False
        self._paused = False
        self._current_response: Optional[Any] = None

    def cancel(self) -> None:
        """Cancel the stream session."""
        self._cancelled = True
        if self._current_response is not None:
            try:
                self._current_response.aclose()
            except Exception:
                pass
            self._current_response = None
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
    ) -> None:
        """Submit a sentence for TTS synthesis."""
        if self._cancelled:
            return
        await self._queue.put((turn_id, sentence, vad, intimacy, character_id))

    async def start(self) -> None:
        """Start the consumer task."""
        self._consumer_task = asyncio.create_task(self._consume())

    async def finish(self) -> None:
        """Signal completion and wait for consumer to finish."""
        await self._queue.put(None)
        if self._consumer_task:
            await self._consumer_task

    async def _check_cache(self, req: Any, text: str) -> Optional[bytes]:
        """Check cache for audio."""
        if not self._cache or not should_cache(text):
            return None
        cache_key = VoiceCache.cache_key(req.voice_id, req.emotion, req.speed, req.pitch, text)
        return await self._cache.get(cache_key)

    async def _send_cached_audio(self, turn_id: str, audio: bytes, fmt: str = "mp3") -> None:
        """Send cached audio as single chunk."""
        await self._send(turn_id, self._global_seq, audio, True, fmt)
        self._global_seq += 1

    async def _stream_tts(self, req: Any, turn_id: str, character_id: str) -> list[bytes]:
        """Stream TTS synthesis and return collected audio chunks."""
        audio_chunks = []
        provider = self._voice.provider

        try:
            if provider.name == "mimo":
                stream = await provider.stream_synthesize(req, character_id)  # type: ignore[call-arg]
            else:
                stream = await provider.stream_synthesize(req)
        except Exception as primary_err:
            fallback = self._voice.fallback_provider
            if fallback and fallback.name != provider.name:
                logger.warning(
                    "tts_stream_provider_failed",
                    provider=provider.name,
                    error=str(primary_err),
                )
                provider = fallback
                stream = await provider.stream_synthesize(req)
            else:
                raise

        self._current_response = getattr(stream, "_response", None)

        async for chunk in stream:
            if self._cancelled:
                return audio_chunks
            if chunk.data:
                audio_chunks.append(chunk.data)
                chunk_fmt = getattr(chunk, "format", "mp3")
                await self._send(
                    turn_id,
                    self._global_seq,
                    chunk.data,
                    chunk.is_last,
                    chunk_fmt,
                )
                self._global_seq += 1

        self._current_response = None
        return audio_chunks

    async def _cache_audio(self, req: Any, text: str, audio_chunks: list[bytes]) -> None:
        """Cache audio if conditions are met."""
        if self._cache and should_cache(text) and audio_chunks:
            cache_key = VoiceCache.cache_key(req.voice_id, req.emotion, req.speed, req.pitch, text)
            full_audio = b"".join(audio_chunks)
            await self._cache.set(cache_key, full_audio)

    async def _process_item(self, item: tuple) -> None:
        """Process a single item from the queue."""
        turn_id, text, vad, intimacy, character_id = item

        try:
            req = self._voice.director.derive(
                text=text,
                character_id=character_id,
                vad=vad,
                intimacy=intimacy,
            )

            # Check cache
            cached_audio = await self._check_cache(req, text)
            if cached_audio:
                await self._send_cached_audio(turn_id, cached_audio)
                return

            # Stream TTS
            audio_chunks = await self._stream_tts(req, turn_id, character_id)

            # Cache result
            await self._cache_audio(req, text, audio_chunks)

        except Exception as e:
            self._current_response = None
            if not self._cancelled:
                logger.error(
                    "tts_stream_failed",
                    error=str(e),
                    text=text[:30] if text else "",
                )

    async def _consume(self) -> None:
        """Consumer loop: process sentences and generate TTS audio."""
        while True:
            while self._paused and not self._cancelled:
                await asyncio.sleep(0.1)

            item = await self._queue.get()
            if item is None or self._cancelled:
                return

            await self._process_item(item)
