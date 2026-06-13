"""MiniMax TTS Provider — per runtime_specs/08_voice.md"""

import uuid
from typing import AsyncGenerator

import httpx
import structlog

from heart.ss08_voice.errors import TTSProviderError
from heart.ss08_voice.types import AudioChunk, TTSRequest, TTSResult

logger = structlog.get_logger(__name__)

_VALID_EMOTIONS = {"happy", "sad", "angry", "fearful", "disgusted", "surprised", "neutral"}


class MiniMaxProvider:
    """MiniMax TTS Provider (speech-2.6-hd)."""

    def __init__(self, api_key: str, group_id: str, base_url: str = "https://api.minimax.io/v1"):
        self._api_key = api_key
        self._group_id = group_id
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=30.0)

    def _build_body(self, req: TTSRequest, stream: bool = False) -> dict:
        """Build request payload with HD model + 32k sample rate + explicit emotion."""
        emotion = req.emotion if req.emotion in _VALID_EMOTIONS else "neutral"
        return {
            "model": "speech-2.6-hd",
            "text": req.text,
            "stream": stream,
            "language_boost": "Chinese",
            "voice_setting": {
                "voice_id": req.voice_id,
                "speed": req.speed,
                "vol": req.volume,
                "pitch": req.pitch,
                "emotion": emotion,
                "english_normalization": True,
                "latex_read": False,
            },
            "audio_setting": {
                "sample_rate": 32000,
                "bitrate": 128000,
                "format": req.format,
                "channel": 1,
            },
        }

    async def synthesize(self, req: TTSRequest) -> TTSResult:
        """Synthesize speech from text (non-streaming)."""
        body = self._build_body(req, stream=False)

        try:
            response = await self._client.post(
                f"{self._base_url}/t2a_v2",
                json=body,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise TTSProviderError(
                f"MiniMax API error: {e.response.status_code} - {e.response.text}",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            raise TTSProviderError(f"MiniMax request failed: {str(e)}") from e

        data = response.json()
        if "data" not in data or "audio" not in data["data"]:
            raise TTSProviderError(f"Invalid MiniMax response: {data}")

        audio_hex = data["data"]["audio"]
        audio_bytes = bytes.fromhex(audio_hex)
        duration_ms = max(1, len(audio_bytes) * 8 // 128) if audio_bytes else 0

        return TTSResult(
            audio=audio_bytes,
            format=req.format,
            duration_ms=duration_ms,
            request_id=str(uuid.uuid4()),
        )

    def stream_synthesize(self, req: TTSRequest) -> AsyncGenerator[AudioChunk, None]:
        """Synthesize speech from text (streaming)."""
        return self._stream_impl(req)

    async def _stream_impl(self, req: TTSRequest) -> AsyncGenerator[AudioChunk, None]:
        body = self._build_body(req, stream=True)

        seq = 0
        try:
            async with self._client.stream(
                "POST",
                f"{self._base_url}/t2a_v2",
                json=body,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue

                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        break

                    try:
                        import json

                        data = json.loads(data_str)

                        if "data" in data and "audio" in data["data"]:
                            audio_hex = data["data"]["audio"]
                            audio_bytes = bytes.fromhex(audio_hex)
                            yield AudioChunk(
                                seq=seq, data=audio_bytes, format=req.format, is_last=False
                            )
                            seq += 1
                    except Exception as e:
                        logger.warning("stream_parse_error", error=str(e))
                        continue

        except httpx.HTTPStatusError as e:
            raise TTSProviderError(
                f"MiniMax stream error: {e.response.status_code}",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            raise TTSProviderError(f"MiniMax stream request failed: {str(e)}") from e

        yield AudioChunk(seq=seq, data=b"", format=req.format, is_last=True)

    def estimate_cost_cents(self, text: str) -> float:
        """Estimate cost in cents for synthesizing the given text."""
        return len(text) * 0.01 / 1000

    @property
    def name(self) -> str:
        """Provider name."""
        return "minimax"
