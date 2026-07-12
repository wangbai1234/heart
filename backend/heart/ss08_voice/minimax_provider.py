"""MiniMax TTS Provider — per runtime_specs/08_voice.md"""

import uuid
from typing import AsyncIterator

import httpx
import structlog

from heart.core.config import settings
from heart.ss08_voice.errors import TTSProviderError
from heart.ss08_voice.types import AudioChunk, TTSRequest, TTSResult

logger = structlog.get_logger(__name__)

# Valid emotion values for MiniMax
_VALID_EMOTIONS = {"happy", "sad", "angry", "fearful", "disgusted", "surprised", "neutral"}


class MiniMaxProvider:
    """MiniMax TTS Provider.

    Defaults to `speech-2.8-hd` so cloned voices can retain better prosody,
    filler-word rendering, and pause naturalness.
    """

    def __init__(self, api_key: str, group_id: str, base_url: str = "https://api.minimax.io/v1"):
        self._api_key = api_key
        self._group_id = group_id
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=30.0)

    def _endpoint(self, path: str) -> str:
        """Build the full t2a URL, appending ?GroupId= when configured.

        Mainland MiniMax (api.minimaxi.com) resolves cloned ``UGC_*`` voice_ids
        via the caller's GroupId. Without it, t2a_v2 returns a bad body ("voice
        not found") which the caller sees as "偏离轨道" via the generic error
        path. Preset voices like ``female-shaonv`` are global and work either
        way — this used to hide the bug on the built-in rin/dorothy path.
        """
        url = f"{self._base_url}{path}"
        if self._group_id:
            sep = "&" if "?" in url else "?"
            return f"{url}{sep}GroupId={self._group_id}"
        return url

    def _build_body(self, req: TTSRequest, stream: bool) -> dict:
        emotion = req.emotion if req.emotion in _VALID_EMOTIONS else "neutral"
        body = {
            "model": settings.minimax_tts_model,
            "text": req.text,
            "voice_setting": {
                "voice_id": req.voice_id,
                "speed": req.speed,
                "vol": req.volume,
                "pitch": req.pitch,
                "emotion": emotion,
                "english_normalization": False,
            },
            "audio_setting": {
                "sample_rate": req.sample_rate,
                "bitrate": 128000,
                "format": req.format,
                "channel": 1,
            },
        }
        if settings.minimax_language_boost:
            body["language_boost"] = settings.minimax_language_boost
        if stream:
            body["stream"] = True
        return body

    async def synthesize(self, req: TTSRequest) -> TTSResult:
        """Synthesize speech from text (non-streaming)."""
        body = self._build_body(req, stream=False)

        try:
            response = await self._client.post(
                self._endpoint("/t2a_v2"),
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
        # MiniMax returns HTTP 200 with a non-zero base_resp.status_code for
        # logical failures (missing GroupId, unknown voice_id, quota, etc.).
        # Surface those as actionable errors instead of masking them behind
        # "Invalid MiniMax response".
        base_resp = data.get("base_resp") if isinstance(data, dict) else None
        if isinstance(base_resp, dict):
            status_code = base_resp.get("status_code")
            if status_code not in (0, None):
                raise TTSProviderError(
                    f"MiniMax logical error: status={status_code} msg={base_resp.get('status_msg', '')}",
                    status_code=int(status_code) if isinstance(status_code, int) else 500,
                )
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
        body = self._build_body(req, stream=True)

        seq = 0
        try:
            async with self._client.stream(
                "POST",
                self._endpoint("/t2a_v2"),
                json=body,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=5.0,
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
                                seq=seq,
                                data=audio_bytes,
                                format=req.format,
                                is_last=False,
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

        # Send last chunk
        yield AudioChunk(
            seq=seq,
            data=b"",
            format=req.format,
            is_last=True,
        )

    def estimate_cost_cents(self, text: str) -> float:
        """Estimate cost in cents for synthesizing the given text."""
        # MiniMax pricing: ~$0.01 per 1000 characters
        return len(text) * 0.01 / 1000

    @property
    def name(self) -> str:
        """Provider name."""
        return "minimax"
