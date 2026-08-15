"""Realtime StreamSession — Fish Audio incremental TTS for a turn.

Mirrors the public surface of ``StreamSession`` (start/submit/finish/cancel/
pause/resume + full_audio/audio_produced/tts_provider_name/is_cancelled) so it
drops into ``routes_chat_ws`` as an alternative session, but instead of
buffering the whole turn and synthesising once (the blocking REST path), it:

  - opens a Fish realtime WebSocket on ``start()``,
  - feeds each sentence to it as ``submit()`` is called,
  - pumps incoming audio to the client as it arrives (a background task),
  - closes the socket on ``finish()``.

This isolates the realtime path from the proven ``StreamSession`` (no changes
to that class) and keeps the risk contained behind the FISH_REALTIME_ENABLED
flag + the caller's fallback-to-REST on ``start()`` failure.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any, Callable, Optional

import structlog

from heart.ss08_voice.fish_realtime_provider import FishRealtimeSession
from heart.ss08_voice.stream_session import _strip_tts_stage_directions

logger = structlog.get_logger(__name__)

# Ceiling for draining audio after the final ``stop`` — bounds a silent server
# so finish() can't hang. The turn-level 45s timeout is the outer backstop.
_DRAIN_TIMEOUT_S = 40.0

SessionFactory = Callable[[str], FishRealtimeSession]

# Per-voice realtime speed overrides, keyed by Fish voice_id (model_id UUID).
# The realtime WS path otherwise renders every voice at speed=1.0, which for a
# few presets reads noticeably faster than their REST preview (previews omit the
# speed field entirely and inherit Fish's REST default). Any voice_id absent
# here keeps 1.0. Fish accepts 0.5–2.0.
#   2fe2aecb… = fish_male_bad ("危险痞帅" / 痞帅浪子) — realtime ran too fast.
_REALTIME_SPEED_OVERRIDES: dict[str, float] = {
    "2fe2aecb-8a8b-45b1-9de1-ddede0c4da63": 0.7,
}


class RealtimeStreamSession:
    """Streams Fish realtime audio for one turn."""

    def __init__(
        self,
        ws_send_audio: Callable[..., Any],
        *,
        api_key: str,
        url: str,
        character_id: str,
        fmt: str = "mp3",
        speed: float = 1.0,
        chunk_length: int = 200,
        latency: str = "balanced",
        tts_model: str = "fishaudio-s21pro-flash",
        session_factory: Optional[SessionFactory] = None,
    ) -> None:
        self._send = ws_send_audio
        self._api_key = api_key
        self._url = url
        self._character_id = character_id
        self._fmt = fmt
        self._speed = speed
        self._chunk_length = chunk_length
        self._latency = latency
        self._tts_model = tts_model
        self._session_factory = session_factory or self._default_session_factory

        self._session: Optional[FishRealtimeSession] = None
        self._reader_task: Optional[asyncio.Task] = None
        self._global_seq = 0
        self._cancelled = False
        self._turn_id: Optional[str] = None
        self._all_audio_chunks: list[bytes] = []
        self._pump_error: Optional[Exception] = None
        self._sentences_submitted = 0

        self.audio_produced = False
        self.tts_provider_name = ""
        # The format of every audio chunk this session emits (mp3 for chat, wav
        # for calls). Callers persisting full_audio MUST consult this: the REST
        # StreamSession exposes the same attribute, and _upload_turn_audio keys
        # off it to pick the right container + content-type. Without it the
        # getattr(..., "audio_format", "") default was "" → mp3 bytes got wrapped
        # as PCM16 WAV and replayed as electrical noise (the "杂音" bug).
        self.audio_format = fmt

    def _default_session_factory(self, model_id: str) -> FishRealtimeSession:
        return FishRealtimeSession(
            api_key=self._api_key,
            url=self._url,
            model_id=model_id,
            fmt=self._fmt,
            speed=self._speed,
            chunk_length=self._chunk_length,
            latency=self._latency,
            tts_model=self._tts_model,
        )

    # ── public surface (matches StreamSession) ──────────────────────────────

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    @property
    def full_audio(self) -> bytes:
        if not self._all_audio_chunks:
            return b""
        return b"".join(self._all_audio_chunks)

    async def start(self) -> None:
        """Open the realtime socket and begin pumping audio.

        Raises on connect/handshake failure so the caller can fall back to the
        REST StreamSession before any audio has been streamed.
        """
        from heart.ss08_voice.voice_catalog import get_voice_id

        model_id = get_voice_id(self._character_id)
        override = _REALTIME_SPEED_OVERRIDES.get(model_id)
        if override is not None:
            self._speed = override
        logger.info(
            "fish_realtime_session_start",
            character_id=self._character_id,
            voice_id=model_id,
            fmt=self._fmt,
            tts_model=self._tts_model,
            url=self._url,
        )
        self._session = self._session_factory(model_id)
        await self._session.open()
        self._reader_task = asyncio.create_task(self._pump_audio())

    async def _pump_audio(self) -> None:
        assert self._session is not None
        chunk_count = 0
        try:
            async for data in self._session.audio_events():
                if self._cancelled:
                    break
                chunk_count += 1
                if chunk_count == 1:
                    logger.info(
                        "fish_realtime_first_audio",
                        chunk_size=len(data),
                        first_bytes=data[:16].hex() if data else "",
                        fmt=self._fmt,
                        sample_rate=(self._session.sample_rate if self._session else None),
                    )
                self._all_audio_chunks.append(data)
                self.audio_produced = True
                self.tts_provider_name = "fish"
                if self._turn_id is not None:
                    sr = self._session.sample_rate if self._session else None
                    await self._send(self._turn_id, self._global_seq, data, False, self._fmt, sr)
                    self._global_seq += 1
        except Exception as e:
            self._pump_error = e
            logger.warning("fish_realtime_pump_error", error=str(e))
        finally:
            logger.info(
                "fish_realtime_pump_done",
                chunks=chunk_count,
                total_bytes=sum(len(c) for c in self._all_audio_chunks),
                sentences_submitted=self._sentences_submitted,
            )

    async def submit(
        self,
        turn_id: str,
        sentence: str,
        vad: dict | None,
        intimacy: float,
        active_emotions: list[Any] | None,
        character_id: str,
    ) -> None:
        if self._cancelled or self._session is None:
            return
        self._turn_id = turn_id
        # _strip_tts_stage_directions only removes （）/【】 actions; any leading
        # [中文指令] the LLM emitted survives and is sent verbatim so Fish S2
        # varies tone sentence by sentence.
        cleaned = _strip_tts_stage_directions(sentence).strip()
        if not cleaned:
            return
        self._sentences_submitted += 1
        logger.info(
            "fish_realtime_submit",
            n=self._sentences_submitted,
            chars=len(cleaned),
        )
        try:
            await self._session.send_text(cleaned)
        except Exception as e:
            logger.warning("fish_realtime_send_text_failed", error=str(e))

    async def finish(self) -> None:
        """Signal end-of-text, drain remaining audio, close the socket."""
        if self._cancelled or self._session is None:
            return
        try:
            await self._session.finish()
            if self._reader_task is not None:
                with contextlib.suppress(asyncio.TimeoutError):
                    await asyncio.wait_for(
                        asyncio.shield(self._reader_task), timeout=_DRAIN_TIMEOUT_S
                    )
        finally:
            await self._session.close()

    def cancel(self) -> None:
        self._cancelled = True
        if self._reader_task is not None and not self._reader_task.done():
            self._reader_task.cancel()
        if self._session is not None:
            with contextlib.suppress(RuntimeError):
                asyncio.create_task(self._session.close())

    def pause(self) -> None:
        # Realtime path does not implement backpressure; audio is small + fast.
        return None

    def resume(self) -> None:
        return None
