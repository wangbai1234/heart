"""Fish Audio realtime TTS session (WebSocket + MessagePack).

Fish's realtime endpoint feeds text sentence-by-sentence and returns audio
incrementally, so the first audio arrives far sooner than the blocking REST
synth (``FishProvider.synthesize``). That low time-to-first-audio is Fish's
"faster than MiMo" selling point.

Protocol (docs.fishaudio.org/.../realtime), MessagePack binary frames:
    connect (Authorization: Bearer <key>, subprotocol realtime.tts.msgpack.v1)
      → server: authenticated
      → client: start { request: { model_id, format, speed, ... } }
      → server: ready
      → client: text { text }  … flush
      → server: audio { data(bytes), audio_sequence, format }  (one or more)
      → client: stop
      → server: finish { reason }
    An ``error`` event closes the connection.

``model_id`` is the Fish voice UUID (our stored clone ``voiceId``).

This module owns ONE session; it does not touch StreamSession, so it can be
unit-tested against a fake in-memory socket via ``ws_factory`` / no live key.
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Awaitable, Callable, Optional

import msgpack
import structlog

from heart.ss08_voice.errors import TTSProviderError

logger = structlog.get_logger(__name__)

_SUBPROTOCOL = "realtime.tts.msgpack.v1"
# Ceiling for the handshake (start → ready). The turn-level 45s timeout also
# covers this, but a local bound gives a clean, fast fallback to REST.
_READY_TIMEOUT_S = 10.0

# A ws_factory takes (url, api_key) and returns an object exposing async
# send(bytes) / recv() -> bytes|str / close(). Injectable for tests.
WsFactory = Callable[[str, str], Awaitable[Any]]


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
    """A single realtime TTS session over one WebSocket connection."""

    def __init__(
        self,
        api_key: str,
        url: str,
        model_id: str,
        fmt: str = "mp3",
        speed: float = 1.0,
        chunk_length: int = 200,
        latency: str = "balanced",
        ws_factory: Optional[WsFactory] = None,
    ) -> None:
        self._api_key = api_key
        self._url = url
        self._model_id = model_id
        self._fmt = fmt
        self._speed = speed
        self._chunk_length = chunk_length
        self._latency = latency
        self._ws_factory = ws_factory or _default_ws_factory
        self._ws: Any = None
        self._closed = False

    async def _send_event(self, event: dict[str, Any]) -> None:
        if self._ws is None:
            raise TTSProviderError("fish realtime: socket not open")
        await self._ws.send(_pack(event))

    async def open(self) -> None:
        """Connect, send ``start``, and wait for ``ready`` (raises on failure)."""
        self._ws = await self._ws_factory(self._url, self._api_key)
        request: dict[str, Any] = {
            "model_id": self._model_id,
            "format": self._fmt,
            "speed": self._speed,
            "chunk_length": self._chunk_length,
            "latency": self._latency,
        }
        await self._send_event({"event": "start", "request": request})

        async def _await_ready() -> None:
            while True:
                frame = await self._ws.recv()
                evt = _unpack(frame)
                etype = evt.get("event")
                if etype == "ready":
                    return
                if etype == "error":
                    raise TTSProviderError(
                        f"fish realtime start error: {evt.get('message') or evt}"
                    )
                # ignore 'authenticated' and any other pre-ready frames

        try:
            await asyncio.wait_for(_await_ready(), timeout=_READY_TIMEOUT_S)
        except (asyncio.TimeoutError, TTSProviderError):
            await self.close()
            raise
        except Exception as e:  # connection dropped mid-handshake, etc.
            await self.close()
            raise TTSProviderError(f"fish realtime handshake failed: {e}") from e

    async def send_text(self, text: str) -> None:
        """Send a sentence and flush it so generation starts promptly."""
        await self._send_event({"event": "text", "text": text})
        await self._send_event({"event": "flush"})

    async def audio_events(self) -> AsyncIterator[bytes]:
        """Yield raw audio bytes as ``audio`` frames arrive; ends on ``finish``.

        Raises TTSProviderError on an ``error`` frame. A closed connection ends
        the iterator cleanly (whatever audio arrived is what the turn gets).
        """
        if self._ws is None:
            raise TTSProviderError("fish realtime: socket not open")
        while True:
            try:
                frame = await self._ws.recv()
            except Exception as e:
                # ConnectionClosed(OK) or transport end → stop iterating.
                name = type(e).__name__
                if "ConnectionClosed" in name or "Cancelled" in name:
                    return
                raise TTSProviderError(f"fish realtime recv error: {e}") from e
            evt = _unpack(frame)
            etype = evt.get("event")
            if etype == "audio":
                data = evt.get("data")
                if data:
                    yield data if isinstance(data, (bytes, bytearray)) else bytes(data)
            elif etype == "finish":
                return
            elif etype == "error":
                raise TTSProviderError(f"fish realtime error: {evt.get('message') or evt}")
            # ignore usage / pong / stray ready

    async def finish(self) -> None:
        """Tell the server no more text is coming."""
        if self._ws is None or self._closed:
            return
        try:
            await self._send_event({"event": "stop"})
        except Exception as e:
            logger.warning("fish_realtime_stop_failed", error=str(e))

    async def close(self) -> None:
        if self._ws is None or self._closed:
            self._closed = True
            return
        self._closed = True
        try:
            await self._ws.close()
        except Exception:
            pass
