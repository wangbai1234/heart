"""MiniMax TTS Provider — per runtime_specs/08_voice.md"""

import uuid
from typing import AsyncIterator

import httpx
import structlog

from heart.ss08_voice.errors import TTSProviderError
from heart.ss08_voice.types import AudioChunk, TTSRequest, TTSResult

logger = structlog.get_logger(__name__)

# Valid emotion values for MiniMax
_VALID_EMOTIONS = {"happy", "sad", "angry", "fearful", "disgusted", "surprised", "neutral"}


class MiniMaxProvider:
    """MiniMax TTS Provider (speech-02-turbo)."""

    def __init__(self, api_key: str, group_id: str, base_url: str = "https://api.minimax.io/v1"):
        self._api_key = api_key
        self._group_id = group_id
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=30.0)

    async def synthesize(self, req: TTSRequest) -> TTSResult:
        """Synthesize speech from text (non-streaming)."""
        emotion = req.emotion if req.emotion in _VALID_EMOTIONS else "neutral"

        body = {
            "model": "speech-02-turbo",
            "text": req.text,
            "voice_setting": {
                "voice_id": req.voice_id,
                "speed": req.speed,
                "vol": req.volume,
                "pitch": req.pitch,
                "emotion": emotion,
            },
            "audio_setting": {
                "sample_rate": req.sample_rate,
                "bitrate": 128000,
                "format": req.format,
                "channel": 1,
            },
        }

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

        # MiniMax returns audio as hex string
        audio_hex = data["data"]["audio"]
        audio_bytes = bytes.fromhex(audio_hex)

        # Calculate duration based on format and bitrate
        # For MP3: duration_ms = (bytes * 8) / (bitrate_bps / 1000)
        # Using 128kbps bitrate: duration_ms = (bytes * 8) / 128
        duration_ms = max(1, len(audio_bytes) * 8 // 128) if audio_bytes else 0

        return TTSResult(
            audio=audio_bytes,
            format=req.format,
            duration_ms=duration_ms,
            request_id=str(uuid.uuid4()),
        )

    async def stream_synthesize(self, req: TTSRequest) -> AsyncIterator[AudioChunk]:
        """Synthesize speech from text (streaming)."""
        # TODO: Implement in VP4
        raise NotImplementedError("stream_synthesize will be implemented in VP4")

    def estimate_cost_cents(self, text: str) -> float:
        """Estimate cost in cents for synthesizing the given text."""
        # MiniMax pricing: ~$0.01 per 1000 characters
        return len(text) * 0.01 / 1000

    @property
    def name(self) -> str:
        """Provider name."""
        return "minimax"
