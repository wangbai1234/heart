"""Stream Session — manages TTS streaming for a turn."""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional

import structlog

from heart.ss08_voice.service import VoiceService

logger = structlog.get_logger(__name__)


class StreamSession:
    """Manages TTS streaming for a single turn.

    Responsible for:
    - Receiving sentence events from orchestrator
    - Running TTS stream synthesis for each sentence
    - Pushing audio chunks to WebSocket
    - Handling cancellation and backpressure
    """

    def __init__(
        self,
        voice_service: VoiceService,
        ws_send_audio: Callable[..., Any],
    ):
        """Initialize stream session.

        Args:
            voice_service: VoiceService instance.
            ws_send_audio: async callable(turn_id, seq, audio_bytes, is_last)
        """
        self._voice = voice_service
        self._send = ws_send_audio
        self._queue: asyncio.Queue[tuple | None] = asyncio.Queue(maxsize=10)
        self._consumer_task: Optional[asyncio.Task] = None
        self._global_seq = 0
        self._cancelled = False
        self._paused = False

    def cancel(self) -> None:
        """Cancel the stream session."""
        self._cancelled = True
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
        await self._queue.put(None)  # Sentinel
        if self._consumer_task:
            await self._consumer_task

    async def _consume(self) -> None:
        """Consumer loop: process sentences and generate TTS audio."""
        while True:
            # Handle backpressure
            while self._paused and not self._cancelled:
                await asyncio.sleep(0.1)

            item = await self._queue.get()
            if item is None or self._cancelled:
                return

            turn_id, text, vad, intimacy, character_id = item

            try:
                # Derive TTS request from state
                req = self._voice.director.derive(
                    text=text,
                    character_id=character_id,
                    vad=vad,
                    intimacy=intimacy,
                )

                # Stream TTS synthesis
                stream = await self._voice.provider.stream_synthesize(req)
                async for chunk in stream:
                    if self._cancelled:
                        return

                    await self._send(
                        turn_id,
                        self._global_seq,
                        chunk.data,
                        chunk.is_last,
                    )
                    self._global_seq += 1

            except Exception as e:
                logger.error(
                    "tts_stream_failed",
                    error=str(e),
                    text=text[:30] if text else "",
                )
