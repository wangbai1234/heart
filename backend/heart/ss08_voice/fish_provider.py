"""Fish Audio TTS Provider.

Fish Audio uses a REST API with multipart/form-data for synthesis and
a WebSocket-based streaming endpoint.  We implement the non-streaming
synthesize path (mp3) here; stream_synthesize falls back to chunking
the full synthesis result.
"""

from __future__ import annotations

import uuid
from typing import AsyncIterator

import httpx
import structlog

from heart.ss08_voice.errors import TTSProviderError
from heart.ss08_voice.types import AudioChunk, TTSRequest, TTSResult

logger = structlog.get_logger(__name__)

_DEFAULT_BASE_URL = "https://api.fish.audio"
_DEFAULT_MODEL = "speech-1.6"


class FishProvider:
    """Fish Audio TTS provider (non-streaming synthesis via REST API)."""

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
        """Synthesize speech using Fish Audio TTS API."""
        audio_format: str = req.format if req.format in ("mp3", "wav", "opus") else "mp3"
        payload = {
            "text": req.text,
            "format": audio_format,
            "mp3_bitrate": 128,
            "normalize": True,
            "latency": "balanced",
        }
        if req.voice_id and req.voice_id != "default":
            payload["reference_id"] = req.voice_id

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/v1/tts",
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
