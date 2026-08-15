"""Fish Audio realtime TTS session (WebSocket + MessagePack, v3 protocol).

Fish's realtime endpoint feeds text sentence-by-sentence and returns audio
incrementally, so the first audio arrives far sooner than the blocking REST
synth (``FishProvider.synthesize``). That low time-to-first-audio is Fish's
"faster than MiMo" selling point.

Protocol (docs.fishaudio.org/.../realtime), MessagePack binary frames, v3:
    connect (Authorization: Bearer <key>, subprotocol realtime.tts.msgpack.v3)
      → server: authenticated (implicit on successful connect)
      → client: start { eventId, mode, request: { voiceId, modelId, format, speed, ... } }
      → server: ready { sessionId, requestId, effectiveRequest }
      → client: input { eventId, text, commit: true }  (one per sentence)
      → server: audio { audio: bytes }  (one or more)
      → client: stop
      → server: finish
    An ``error`` event closes the connection.

``voiceId`` is the Fish voice UUID (our stored clone ID).
``modelId`` is the Fish TTS model (e.g. "fishaudio-s21pro-flash").

This module owns ONE session; it does not touch StreamSession, so it can be
unit-tested against a fake in-memory socket via ``ws_factory`` / no live key.
"""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from typing import Any, AsyncIterator, Awaitable, Callable, Optional

import msgpack
import structlog

from heart.ss08_voice.errors import TTSProviderError

logger = structlog.get_logger(__name__)

_SUBPROTOCOL = "realtime.tts.msgpack.v3"
_READY_TIMEOUT_S = 10.0
_OPEN_MAX_ATTEMPTS = 3
_OPEN_RETRY_DELAY_S = 0.25

WsFactory = Callable[[str, str], Awaitable[Any]]


def _evt_id() -> str:
    return uuid.uuid4().hex[:16]


async def _default_ws_factory(url: str, api_key: str) -> Any:
    import websockets

    return await websockets.connect(
        url,
        additional_headers={"Authorization": f"Bearer {api_key}"},
        subprotocols=[_SUBPROTOCOL],  # type: ignore[list-item]
        max_size=None,
    )


def _pack(obj: dict[str, Any]) -> bytes:
    return msgpack.packb(obj, use_bin_type=True)


def _unpack(frame: Any) -> dict[str, Any]:
    if isinstance(frame, str):
        frame = frame.encode()
    obj = msgpack.unpackb(frame, raw=False)
    return obj if isinstance(obj, dict) else {}


class FishRealtimeSession:
    """A single realtime TTS session over one WebSocket connection (v3 protocol)."""

    def __init__(
        self,
        api_key: str,
        url: str,
        model_id: str,
        fmt: str = "mp3",
        speed: float = 1.0,
        chunk_length: int = 200,
        latency: str = "balanced",
        tts_model: str = "fishaudio-s21pro-flash",
        ws_factory: Optional[WsFactory] = None,
    ) -> None:
        self._api_key = api_key
        self._url = url
        self._model_id = model_id  # Fish voice UUID (voiceId)
        self._fmt = fmt
        self._speed = speed
        self._chunk_length = chunk_length
        self._latency = latency
        self._tts_model = tts_model
        self._ws_factory = ws_factory or _default_ws_factory
        self._ws: Any = None
        self._closed = False
        self._retryable = False
        self._sample_rate: Optional[int] = None
        # Streaming lifecycle: sentences are appended with commit=false (see
        # send_text), finalized by a single flush in finish(), then the session
        # is closed with stop. These flags track that progression.
        self._sent_text = False
        self._flush_sent = False
        self._stop_sent = False

    @property
    def sample_rate(self) -> Optional[int]:
        return self._sample_rate

    async def _send_event(self, event: dict[str, Any]) -> None:
        if self._ws is None:
            raise TTSProviderError("fish realtime: socket not open")
        await self._ws.send(_pack(event))

    async def _open_once(self) -> None:
        """One connect + start + await-ready cycle. Sets ``_retryable`` on error."""
        self._retryable = False
        self._ws = await self._ws_factory(self._url, self._api_key)
        request: dict[str, Any] = {
            "voiceId": self._model_id,
            "modelId": self._tts_model,
            "format": self._fmt,
            "speed": self._speed,
            "chunkLength": self._chunk_length,
            "latency": self._latency,
        }
        await self._send_event(
            {
                "event": "start",
                "eventId": _evt_id(),
                # reliable mode: client controls segmentation via a single
                # `flush` after buffering all sentences (input commit:false).
                # simple mode rejects `flush` with invalid_state, which dropped
                # every sentence after the first.
                "mode": "reliable",
                "request": request,
            }
        )

        async def _await_ready() -> None:
            while True:
                frame = await self._ws.recv()
                evt = _unpack(frame)
                etype = evt.get("event")
                if etype == "ready":
                    sr = evt.get("sample_rate") or evt.get("sampleRate")
                    if isinstance(sr, int) and sr > 0:
                        self._sample_rate = sr
                    return
                if etype == "error":
                    self._retryable = bool(evt.get("retryable"))
                    raise TTSProviderError(
                        f"fish realtime start error: {evt.get('message') or evt}"
                    )

        try:
            await asyncio.wait_for(_await_ready(), timeout=_READY_TIMEOUT_S)
        except asyncio.TimeoutError:
            self._retryable = True
            await self.close()
            raise
        except TTSProviderError:
            await self.close()
            raise
        except Exception as e:
            self._retryable = True
            await self.close()
            raise TTSProviderError(f"fish realtime handshake failed: {e}") from e

    async def open(self) -> None:
        """Connect, send ``start``, wait for ``ready`` — retrying transient fails."""
        last_exc: Optional[BaseException] = None
        for attempt in range(1, _OPEN_MAX_ATTEMPTS + 1):
            self._closed = False
            try:
                await self._open_once()
                return
            except TTSProviderError as e:
                last_exc = e
                if not self._retryable or attempt >= _OPEN_MAX_ATTEMPTS:
                    raise
                logger.warning(
                    "fish_realtime_open_retry",
                    attempt=attempt,
                    max_attempts=_OPEN_MAX_ATTEMPTS,
                    error=str(e),
                )
                await asyncio.sleep(_OPEN_RETRY_DELAY_S)
        if last_exc is not None:
            raise last_exc

    async def send_text(self, text: str) -> None:
        """Append a sentence to the buffer WITHOUT finalizing the segment.

        v3 ``commit: true`` means "append AND finalize/trigger this segment now",
        which CLOSES the segment — the server then emits segment_completed +
        finish and DROPS every later input. Streaming a reply sentence-by-sentence
        with commit=true therefore only ever synthesizes the first sentence (the
        "只播第一句" bug). We append with commit=false and finalize the whole
        buffer once with a single ``flush`` in finish(). The server still
        auto-synthesizes incrementally as the buffer crosses chunkLength, so
        time-to-first-audio is unchanged.
        """
        self._sent_text = True
        await self._send_event(
            {
                "event": "input",
                "eventId": _evt_id(),
                "text": text,
                "commit": False,
            }
        )

    def _extract_audio_bytes(self, evt: dict[str, Any]) -> Optional[bytes]:
        """Pull the binary audio payload from an audio event.

        v3 puts audio bytes in the ``audio`` field directly.
        """
        sr = evt.get("sample_rate") or evt.get("sampleRate")
        if isinstance(sr, int) and sr > 0:
            self._sample_rate = sr
        data = evt.get("audio")
        if data is None:
            data = evt.get("data")
        if not data:
            return None
        return bytes(data)

    async def _recv_event(self, frame_count: int) -> Optional[dict[str, Any]]:
        """Receive+unpack one frame. Returns None on a clean connection close."""
        try:
            frame = await self._ws.recv()
        except Exception as e:
            name = type(e).__name__
            if "ConnectionClosed" in name or "Cancelled" in name:
                logger.info("fish_realtime_conn_closed", frames_received=frame_count)
                return None
            raise TTSProviderError(f"fish realtime recv error: {e}") from e
        evt = _unpack(frame)
        etype = evt.get("event")
        # TEMP diagnostic: log every non-audio control event with its frame index
        # so we can see the exact v3 event sequence (segment_completed vs finish
        # vs stop timing) driving the "only first sentence plays" truncation.
        if etype == "error" or etype == "warning":
            logger.info("fish_realtime_event", event_type=etype, frame=frame_count, detail=evt)
        elif etype != "audio":
            logger.info("fish_realtime_event", event_type=etype, frame=frame_count)
        elif frame_count == 0:
            logger.info(
                "fish_realtime_first_event",
                event_type=etype,
                keys=list(evt.keys()),
            )
        return evt

    async def audio_events(self) -> AsyncIterator[bytes]:
        """Yield raw audio bytes as ``audio`` frames arrive; ends on ``finish``.

        Raises TTSProviderError on an ``error`` frame. A closed connection ends
        the iterator cleanly (whatever audio arrived is what the turn gets).
        """
        if self._ws is None:
            raise TTSProviderError("fish realtime: socket not open")
        frame_count = 0
        while True:
            evt = await self._recv_event(frame_count)
            if evt is None:
                return
            etype = evt.get("event")
            frame_count += 1
            if etype == "audio":
                payload = self._extract_audio_bytes(evt)
                if payload:
                    yield payload
            elif self._handle_control_event(evt, etype, frame_count):
                return

    def _handle_control_event(
        self, evt: dict[str, Any], etype: Optional[str], frame_count: int
    ) -> bool:
        """Process a non-audio event. Returns True when the reader should stop.

        Raises TTSProviderError on an ``error`` frame. ``finish`` ends the reader.
        Other control frames (segment_accepted/segment_completed/usage/pong/
        input_ack/warning) carry no audio and are ignored.
        """
        if etype == "error":
            logger.warning(
                "fish_realtime_error_frame",
                frame=frame_count,
                flush_sent=self._flush_sent,
                detail=evt,
            )
            raise TTSProviderError(f"fish realtime error: {evt.get('message') or evt}")
        if etype == "finish":
            # After we flush(), the server synthesizes the whole buffer, streams
            # the remaining audio, then emits finish — that is the real end of the
            # reply, so terminate the reader. A finish BEFORE flush would mean the
            # server closed the segment early; nothing more is coming either, so
            # end then too. (We only ever flush once, at end-of-text.)
            logger.info(
                "fish_realtime_finish",
                frames=frame_count,
                flush_sent=self._flush_sent,
            )
            return True
        return False

    async def finish(self) -> None:
        """Finalize the buffered text, then end the session.

        All sentences were appended with ``commit: false`` (see send_text), so
        the buffer is not yet finalized. ``flush`` forces synthesis of the whole
        remaining buffer WITHOUT closing the connection; the server then streams
        the tail audio and emits ``finish``. We send ``stop`` after flush to end
        the session. Skipping flush would drop any un-synthesized tail — never
        rely on ``stop`` alone to flush.
        """
        if self._ws is None or self._closed:
            return
        # Only flush here. The reader then drains the flushed tail audio until the
        # server emits finish; stop is sent in close() afterwards so it can never
        # race ahead and truncate audio the server is still streaming.
        if self._sent_text:
            self._flush_sent = True
            try:
                await self._send_event({"event": "flush", "eventId": _evt_id()})
            except Exception as e:
                logger.warning("fish_realtime_flush_failed", error=str(e))

    async def close(self) -> None:
        if self._ws is None or self._closed:
            self._closed = True
            return
        # Best-effort session end. By now the reader has consumed all flushed
        # audio (it returns on the server finish), so stop is pure cleanup.
        if not self._stop_sent:
            self._stop_sent = True
            with contextlib.suppress(Exception):
                await self._send_event({"event": "stop", "eventId": _evt_id()})
        self._closed = True
        try:
            await self._ws.close()
        except Exception:
            pass
