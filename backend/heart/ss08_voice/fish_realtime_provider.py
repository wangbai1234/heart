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
# Fish flags transient start failures with error.retryable=True (e.g. a cold
# backend or a momentary gateway hiccup). Re-dialing once or twice recovers the
# turn on the realtime path instead of dropping it to the slower REST fallback.
# Kept tiny so a genuinely-down realtime service still fails fast to REST.
_OPEN_MAX_ATTEMPTS = 3
_OPEN_RETRY_DELAY_S = 0.25

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
        # Set by _open_once when a start failure is safe to re-dial (Fish
        # error.retryable, a dropped socket, or a silent handshake timeout).
        self._retryable = False
        # For pcm/wav formats Fish reports the real sample rate on the ready
        # (and every audio) event; the client must honour it or playback pitch
        # and duration drift. None until the first frame that carries it.
        self._sample_rate: Optional[int] = None

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
                    sr = evt.get("sample_rate")
                    if isinstance(sr, int) and sr > 0:
                        self._sample_rate = sr
                    return
                if etype == "error":
                    # Carry Fish's retryable hint out so open() can re-dial.
                    self._retryable = bool(evt.get("retryable"))
                    raise TTSProviderError(
                        f"fish realtime start error: {evt.get('message') or evt}"
                    )
                # ignore 'authenticated' and any other pre-ready frames

        try:
            await asyncio.wait_for(_await_ready(), timeout=_READY_TIMEOUT_S)
        except asyncio.TimeoutError:
            # A silent handshake is transient far more often than not — let the
            # retry loop re-dial rather than falling straight through to REST.
            self._retryable = True
            await self.close()
            raise
        except TTSProviderError:
            await self.close()
            raise
        except Exception as e:  # connection dropped mid-handshake, etc.
            self._retryable = True
            await self.close()
            raise TTSProviderError(f"fish realtime handshake failed: {e}") from e

    async def open(self) -> None:
        """Connect, send ``start``, wait for ``ready`` — retrying transient fails.

        Fish marks recoverable start failures with ``error.retryable``; a dropped
        or silent handshake is treated the same. We re-dial up to
        ``_OPEN_MAX_ATTEMPTS`` before surfacing the error so the caller falls back
        to REST. A non-retryable error (bad model_id, auth) raises immediately.
        """
        last_exc: Optional[BaseException] = None
        for attempt in range(1, _OPEN_MAX_ATTEMPTS + 1):
            # A prior failed attempt may have marked the session closed; reset so
            # the fresh socket from _open_once isn't torn down by a stale flag.
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
        # Unreachable (loop either returns or raises), but keeps mypy happy.
        if last_exc is not None:
            raise last_exc

    async def send_text(self, text: str) -> None:
        """Send a sentence and flush it so generation starts promptly."""
        await self._send_event({"event": "text", "text": text})
        await self._send_event({"event": "flush"})

    def _extract_audio_bytes(self, evt: dict[str, Any]) -> Optional[bytes]:
        """Pull sample_rate (side effect) and the binary payload from an audio evt.

        The mp3 path proved ``data`` is the payload key on this build of Fish;
        the docs also list ``audio`` — accept whichever is present.
        """
        sr = evt.get("sample_rate")
        if isinstance(sr, int) and sr > 0:
            self._sample_rate = sr
        data = evt.get("data")
        if data is None:
            data = evt.get("audio")
        if not data:
            return None
        return bytes(data)

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
                payload = self._extract_audio_bytes(evt)
                if payload:
                    yield payload
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
