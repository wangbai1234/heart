"""Qwen ASR provider — Aliyun DashScope realtime speech-to-text (WebSocket).

DashScope exposes an OpenAI-realtime-style event protocol for streaming ASR:

    connect  wss://.../api-ws/v1/realtime?model=<realtime_model>
             (Authorization: Bearer <key>)
      → server: session.created
      → client: session.update { session: { input_audio_format, sample_rate,
                 input_audio_transcription:{language}, turn_detection } }
      → client: input_audio_buffer.append { audio: <base64 pcm16> }  … (N frames)
      → client: input_audio_buffer.commit          (manual mode: end of utterance)
      → server: conversation.item.input_audio_transcription.text       (partial)
      → server: conversation.item.input_audio_transcription.completed   (final)
      → client: session.finish
      → server: session.finished

We run **manual mode** (``turn_detection: null``): the client (push-to-talk on
the call page, or the one-shot ``transcribe`` for chat) owns the utterance
boundary and sends ``commit`` explicitly. This keeps the "按住说话，边说边转，
松手即出转写" contract without server VAD reshaping turns.

Two entry points share one session implementation:

  - ``QwenAsrProvider.transcribe(audio, mime)`` — one-shot (voice **chat**).
    Drop-in for ``MiMoProvider.transcribe`` (same signature) so ``/transcribe``
    swaps provider with no route changes. Feeds the whole clip, commits, awaits
    the final transcript.
  - ``QwenAsrSession`` — the live session the streaming call WS bridges to.
"""

from __future__ import annotations

import asyncio
import base64
import json
import uuid
from typing import Any, AsyncIterator, Awaitable, Callable, Optional

import structlog

from heart.ss08_voice.errors import TTSProviderError

logger = structlog.get_logger(__name__)

# Handshake ceiling (connect → session.created). A local bound gives a clean,
# fast fallback to MiMo on the one-shot path.
_READY_TIMEOUT_S = 10.0
# Ceiling for the final transcript after commit — bounds a silent server so the
# one-shot transcribe() can't hang. Streaming path relays partials meanwhile.
_FINAL_TIMEOUT_S = 30.0
# ~100ms @ 16kHz/16-bit mono. The realtime spec's typical append size.
_FRAME_BYTES = 3200

# A ws_factory takes (url, api_key) and returns an object exposing async
# send(str|bytes) / recv() -> str|bytes / close(). Injectable for tests.
WsFactory = Callable[[str, str], Awaitable[Any]]


async def _default_ws_factory(url: str, api_key: str) -> Any:
    import ssl

    import websockets

    # Verify TLS against certifi's CA bundle explicitly. The stdlib default
    # store is unreliable across environments (e.g. macOS Python.framework ships
    # without one), which would otherwise fail the DashScope handshake with
    # CERTIFICATE_VERIFY_FAILED. certifi is already a transitive dep via httpx.
    ssl_ctx = ssl.create_default_context()
    try:
        import certifi

        ssl_ctx.load_verify_locations(certifi.where())
    except Exception:
        pass

    return await websockets.connect(
        url,
        additional_headers={"Authorization": f"Bearer {api_key}"},
        max_size=None,
        ssl=ssl_ctx,
    )


def _evt_id() -> str:
    return f"evt_{uuid.uuid4().hex[:16]}"


def _wav_to_pcm16(data: bytes) -> bytes:
    """Extract raw little-endian PCM16 samples from a WAV container.

    The realtime endpoint wants raw ``pcm`` frames, not a WAV file. Frontend
    recordings are 16kHz/mono/16-bit WAV (see web audioRecorder.blobToWav16k),
    so we walk the RIFF chunks and return the ``data`` chunk payload. If the
    bytes aren't a WAV (no RIFF/WAVE header) we assume they're already raw PCM
    and return them unchanged.
    """
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        return data
    pos = 12
    n = len(data)
    while pos + 8 <= n:
        chunk_id = data[pos : pos + 4]
        chunk_size = int.from_bytes(data[pos + 4 : pos + 8], "little")
        body_start = pos + 8
        if chunk_id == b"data":
            return data[body_start : body_start + chunk_size]
        # chunks are word-aligned; skip padding byte on odd sizes
        pos = body_start + chunk_size + (chunk_size & 1)
    return b""


def _extract_transcript_text(evt: dict[str, Any]) -> str:
    """Pull transcript text from a transcription event, tolerant of shape.

    DashScope has shipped the text under a few keys across model versions
    (``text`` on the event, ``transcript`` on the event, or nested under a
    ``delta`` / ``transcription`` object). Accept whichever is present so a
    minor API shape change doesn't silently drop transcripts.
    """
    for key in ("text", "transcript", "delta"):
        val = evt.get(key)
        if isinstance(val, str) and val:
            return val
    trans = evt.get("transcription")
    if isinstance(trans, dict):
        val = trans.get("text") or trans.get("transcript")
        if isinstance(val, str):
            return val
    if isinstance(trans, str):
        return trans
    return ""


class QwenAsrSession:
    """A single realtime ASR session over one WebSocket connection.

    Manual-mode: caller sends audio via ``append`` then signals end-of-utterance
    with ``commit``; ``events()`` yields ``("partial", text)`` / ``("final",
    text)`` tuples until the session ends. ``transcribe_bytes`` is the one-shot
    convenience used by voice chat.
    """

    def __init__(
        self,
        api_key: str,
        ws_url: str,
        model: str,
        *,
        language: str = "zh",
        sample_rate: int = 16000,
        ws_factory: Optional[WsFactory] = None,
    ) -> None:
        self._api_key = api_key
        # model rides as a query param per the realtime spec.
        sep = "&" if "?" in ws_url else "?"
        self._url = f"{ws_url}{sep}model={model}"
        self._model = model
        self._language = language
        self._sample_rate = sample_rate
        self._ws_factory = ws_factory or _default_ws_factory
        self._ws: Any = None
        self._closed = False

    async def _send(self, event: dict[str, Any]) -> None:
        if self._ws is None:
            raise TTSProviderError("qwen asr: socket not open")
        await self._ws.send(json.dumps(event))

    async def open(self) -> None:
        """Connect, wait for ``session.created``, push our session config."""
        self._ws = await self._ws_factory(self._url, self._api_key)

        async def _await_created() -> None:
            while True:
                frame = await self._ws.recv()
                evt = _decode(frame)
                etype = evt.get("type")
                if etype == "session.created":
                    return
                if etype == "error":
                    raise TTSProviderError(f"qwen asr session error: {_err(evt)}")

        try:
            await asyncio.wait_for(_await_created(), timeout=_READY_TIMEOUT_S)
        except (asyncio.TimeoutError, TTSProviderError):
            await self.close()
            raise
        except Exception as e:
            await self.close()
            raise TTSProviderError(f"qwen asr handshake failed: {e}") from e

        # Manual mode: turn_detection null → the client owns utterance
        # boundaries (push-to-talk release / one-shot commit).
        await self._send(
            {
                "event_id": _evt_id(),
                "type": "session.update",
                "session": {
                    "modalities": ["text"],
                    "input_audio_format": "pcm",
                    "sample_rate": self._sample_rate,
                    "input_audio_transcription": {"language": self._language},
                    "turn_detection": None,
                },
            }
        )

    async def append(self, pcm: bytes) -> None:
        """Append a raw PCM16 chunk to the input buffer."""
        if self._closed or self._ws is None or not pcm:
            return
        await self._send(
            {
                "event_id": _evt_id(),
                "type": "input_audio_buffer.append",
                "audio": base64.b64encode(pcm).decode("ascii"),
            }
        )

    async def commit(self) -> None:
        """Signal end-of-utterance (manual mode boundary)."""
        if self._closed or self._ws is None:
            return
        await self._send({"event_id": _evt_id(), "type": "input_audio_buffer.commit"})

    async def events(self) -> AsyncIterator[tuple[str, str]]:
        """Yield ``(kind, text)`` where kind ∈ {"partial", "final"}.

        Ends when the session finishes or the socket closes. Raises
        TTSProviderError on an ``error`` frame.
        """
        if self._ws is None:
            raise TTSProviderError("qwen asr: socket not open")
        while True:
            try:
                frame = await self._ws.recv()
            except Exception as e:
                name = type(e).__name__
                if "ConnectionClosed" in name or "Cancelled" in name:
                    return
                raise TTSProviderError(f"qwen asr recv error: {e}") from e
            evt = _decode(frame)
            etype = evt.get("type", "")
            if etype.endswith("input_audio_transcription.completed"):
                yield ("final", _extract_transcript_text(evt))
            elif etype.endswith("input_audio_transcription.text") or etype.endswith(
                "input_audio_transcription.delta"
            ):
                text = _extract_transcript_text(evt)
                if text:
                    yield ("partial", text)
            elif etype in ("session.finished", "session.finish"):
                return
            elif etype == "error":
                raise TTSProviderError(f"qwen asr error: {_err(evt)}")
            # ignore speech_started/stopped, committed, session.updated, etc.

    async def finish(self) -> None:
        if self._ws is None or self._closed:
            return
        try:
            await self._send({"event_id": _evt_id(), "type": "session.finish"})
        except Exception as e:
            logger.warning("qwen_asr_finish_failed", error=str(e))

    async def close(self) -> None:
        if self._ws is None or self._closed:
            self._closed = True
            return
        self._closed = True
        try:
            await self._ws.close()
        except Exception:
            pass

    async def transcribe_bytes(self, pcm: bytes) -> str:
        """One-shot: append all PCM, commit, await the final transcript.

        Accumulates partials as a fallback in case the server closes without a
        distinct ``completed`` frame (returns the latest partial then).
        """
        # Feed in realtime-sized frames; some gateways reject one huge append.
        for i in range(0, len(pcm), _FRAME_BYTES):
            await self.append(pcm[i : i + _FRAME_BYTES])
        await self.commit()
        await self.finish()

        latest = ""

        async def _collect() -> str:
            nonlocal latest
            async for kind, text in self.events():
                if kind == "final":
                    return text
                if text:
                    latest = text
            return latest

        try:
            return (await asyncio.wait_for(_collect(), timeout=_FINAL_TIMEOUT_S)).strip()
        except asyncio.TimeoutError:
            logger.warning("qwen_asr_final_timeout", latest_len=len(latest))
            return latest.strip()


def _decode(frame: Any) -> dict[str, Any]:
    if isinstance(frame, (bytes, bytearray)):
        frame = frame.decode("utf-8", errors="replace")
    try:
        obj = json.loads(frame)
    except (json.JSONDecodeError, TypeError):
        return {}
    return obj if isinstance(obj, dict) else {}


def _err(evt: dict[str, Any]) -> str:
    err = evt.get("error")
    if isinstance(err, dict):
        return str(err.get("message") or err)
    return str(err or evt)


class QwenAsrProvider:
    """Qwen (DashScope) ASR provider.

    ``transcribe`` matches ``MiMoProvider.transcribe`` so the ``/transcribe``
    route swaps provider with no changes. ``open_session`` mints a live
    ``QwenAsrSession`` for the streaming call WS to bridge to.
    """

    def __init__(
        self,
        api_key: str,
        ws_url: str,
        model: str = "qwen3-asr-flash",
        realtime_model: str = "qwen3-asr-flash-realtime",
        *,
        ws_factory: Optional[WsFactory] = None,
    ) -> None:
        self._api_key = api_key
        self._ws_url = ws_url
        self._model = model
        self._realtime_model = realtime_model
        self._ws_factory = ws_factory

    def open_session(self, *, language: str = "zh", sample_rate: int = 16000) -> QwenAsrSession:
        """Create a realtime session (used by the streaming call endpoint)."""
        return QwenAsrSession(
            api_key=self._api_key,
            ws_url=self._ws_url,
            model=self._realtime_model,
            language=language,
            sample_rate=sample_rate,
            ws_factory=self._ws_factory,
        )

    async def transcribe(
        self,
        audio: bytes,
        mime: str = "audio/wav",
        language: str = "auto",
        asr_model: str | None = None,
    ) -> str:
        """Transcribe audio bytes → text (one-shot, voice-chat path).

        Signature mirrors ``MiMoProvider.transcribe`` (``asr_model`` accepted and
        ignored — the realtime model is fixed per session). ``language='auto'``
        maps to zh (DashScope realtime wants a concrete language code).
        """
        pcm = _wav_to_pcm16(audio)
        if not pcm:
            logger.warning("qwen_asr_no_pcm", mime=mime, raw_len=len(audio))
            return ""
        lang = "zh" if language in ("auto", "", None) else language
        session = QwenAsrSession(
            api_key=self._api_key,
            ws_url=self._ws_url,
            model=self._realtime_model,
            language=lang,
            ws_factory=self._ws_factory,
        )
        await session.open()
        try:
            transcript = await session.transcribe_bytes(pcm)
        finally:
            await session.close()
        logger.info(
            "qwen_asr_transcribed",
            length=len(audio),
            pcm_len=len(pcm),
            transcript_len=len(transcript),
        )
        return transcript

    @property
    def name(self) -> str:
        return "qwen_asr"
