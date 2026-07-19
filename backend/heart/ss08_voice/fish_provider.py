"""Fish Audio TTS Provider (fishaudio.org open API gateway).

Targets the ``/api/open/v1`` gateway contract:
  - Synthesis:   POST {base}/speech/tts  (JSON: text/voiceId/modelId/format)
                 → binary audio (audio/mpeg | audio/wav)
  - Voice clone: POST {base}/voices      (multipart: name + audioFiles[])
                 → JSON { voiceId }

``base`` is expected to already include the ``/api/open/v1`` prefix
(FISH_BASE_URL). ``model`` is the backbone modelId (e.g. fishaudio-s21pro-flash).
"""

from __future__ import annotations

import uuid
from typing import AsyncIterator

import httpx
import structlog

from heart.ss08_voice.errors import TTSProviderError
from heart.ss08_voice.types import AudioChunk, TTSRequest, TTSResult

logger = structlog.get_logger(__name__)

_DEFAULT_BASE_URL = "https://fishaudio.org/api/open/v1"
_DEFAULT_MODEL = "fishaudio-s21pro-flash"


class FishProvider:
    """Fish Audio TTS provider (synchronous REST synthesis + voice clone)."""

    def __init__(
        self,
        api_key: str,
        base_url: str = _DEFAULT_BASE_URL,
        model: str = _DEFAULT_MODEL,
        timeout: float = 60.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "fish"

    def estimate_cost_cents(self, text: str) -> float:
        return 0.0

    async def synthesize(self, req: TTSRequest) -> TTSResult:
        """Synthesize speech via POST {base}/speech/tts (returns binary audio)."""
        audio_format: str = req.format if req.format in ("mp3", "wav") else "mp3"
        payload: dict = {"text": req.text, "format": audio_format}
        # The cloned voice is selected by voiceId; the backbone engine by modelId.
        if req.voice_id and req.voice_id != "default":
            payload["voiceId"] = req.voice_id
        if self._model:
            payload["modelId"] = self._model
        if req.speed and req.speed != 1.0:
            payload["speed"] = req.speed

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/speech/tts",
                    json=payload,
                    headers=headers,
                )
                if resp.status_code != 200:
                    raise TTSProviderError(
                        f"Fish Audio TTS error {resp.status_code}: {resp.text[:200]}"
                    )
                audio_bytes = resp.content
        except httpx.TimeoutException as e:
            raise TTSProviderError(f"Fish Audio TTS timeout: {e}") from e
        except httpx.HTTPError as e:
            raise TTSProviderError(f"Fish Audio TTS HTTP error: {e}") from e

        # mp3 @ ~128 kbps estimate; wav is PCM so this is a loose upper bound.
        duration_ms = max(1, int(len(audio_bytes) / (128 * 1000 / 8) * 1000))
        return TTSResult(
            audio=audio_bytes,
            format=audio_format,
            duration_ms=duration_ms,
            request_id=str(uuid.uuid4()),
        )

    async def stream_synthesize(self, req: TTSRequest) -> AsyncIterator[AudioChunk]:
        """Streaming via chunked synthesis — yields single chunk with full audio."""
        result = await self.synthesize(req)
        yield AudioChunk(seq=0, data=result.audio, format=result.format, is_last=True)

    async def clone_from_bytes(
        self, audio: bytes, title: str, filename: str = "sample.wav", mime: str = "audio/wav"
    ) -> str:
        """Create a Fish voice model from raw audio bytes; return its voiceId.

        POSTs multipart to {base}/voices (field ``name`` + file field
        ``audioFiles``) — no public URL needed, so it works for local seed
        files. Raises TTSProviderError on failure. Used by the built-in clone
        seeder (scripts/seed_builtin_clones.py).
        """
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{self._base_url}/voices",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    data={"name": title},
                    files={"audioFiles": (filename, audio, mime)},
                )
        except httpx.HTTPError as e:
            raise TTSProviderError(f"Fish clone HTTP error: {e}") from e

        if resp.status_code not in (200, 201):
            raise TTSProviderError(f"Fish clone error {resp.status_code}: {resp.text[:300]}")
        body = resp.json()
        voice_id = body.get("voiceId") or body.get("_id")
        if not voice_id:
            raise TTSProviderError(f"Fish clone returned no voiceId: {resp.text[:200]}")
        return voice_id
