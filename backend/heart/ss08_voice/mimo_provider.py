"""MiMo TTS Provider — MiMo voicedesign v2.5 with text-based voice customization.

MiMo voicedesign uses natural-language voice descriptions in the user message
to shape the assistant audio output.  The assistant message carries emotion tags
+ text that the model speaks.

Audio data from MiMo is Base64-encoded (not hex).
"""

from __future__ import annotations

import base64
import json
import uuid
from typing import Any, AsyncGenerator

import httpx
import structlog

from heart.ss08_voice.errors import TTSProviderError
from heart.ss08_voice.types import AudioChunk, TTSRequest, TTSResult

logger = structlog.get_logger(__name__)

_VALID_EMOTIONS = {"happy", "sad", "angry", "fearful", "disgusted", "surprised", "neutral"}

_VOICE_DESCRIPTIONS: dict[str, str] = {
    "rin": (
        "一位25岁左右的温柔女性，音色柔和知性，略带成熟女性的磁性。"
        "语速偏慢（0.9倍速），咬字清晰，情绪温柔体贴，像学姐在耐心解答问题。"
        "音质温暖优雅，共鸣位置靠前，避免过于甜腻。"
    ),
    "dorothy": (
        "一位15岁左右的活泼少女，音色明亮清脆，充满元气和活力。"
        "语速正常（1.0倍速），略带少女的跳跃感和灵动感。"
        "情绪基调元气活力，像朋友在分享趣事，音质轻盈不沉闷，共鸣位置靠上，"
        "带有青春少女的天真感。"
    ),
}

_EMOTION_DIRECTIVES: dict[str, str] = {
    "happy": "用欢快明亮的语气",
    "sad": "用低沉温柔的语气",
    "angry": "用果断有力的语气",
    "fearful": "用紧张不安的语气",
    "disgusted": "用略带抗拒的语气",
    "surprised": "用惊讶好奇的语气",
    "neutral": "用自然平和的语气",
}

_EMOTION_TAGS: dict[str, str] = {
    "happy": "(开心)",
    "sad": "(悲伤)",
    "angry": "(生气)",
    "fearful": "(害怕)",
    "disgusted": "(厌恶)",
    "surprised": "(惊讶)",
    "neutral": "",
}

_CHUNK_SIZE = 8192  # ~170 ms @ 24 kHz PCM16


class MiMoCancellableStream:
    """Wraps an httpx async stream with cancel() for MiMo voicedesign.

    voicedesign returns a single full response (not true streaming), so we
    chunk the complete audio post-facto.
    """

    def __init__(self, response_cm: Any, character_id: str, fmt: str = "pcm16") -> None:
        self._response_cm = response_cm
        self._response: Any = None
        self._cancelled = False
        self._fmt = fmt
        self._character_id = character_id

    async def cancel(self) -> None:
        self._cancelled = True
        if self._response is not None:
            try:
                await self._response.aclose()
            except Exception:
                pass

    async def __aiter__(self) -> AsyncGenerator[AudioChunk, None]:  # type: ignore[override]
        async with self._response_cm as response:
            self._response = response
            response.raise_for_status()

            full_data = await response.aread()
            if self._cancelled:
                return

            audio_bytes = _parse_mimo_response(full_data)
            if not audio_bytes:
                logger.warning("mimo_empty_audio", character=self._character_id)
                yield AudioChunk(seq=0, data=b"", format=self._fmt, is_last=True)
                return

            seq = 0
            total = len(audio_bytes)
            for i in range(0, total, _CHUNK_SIZE):
                if self._cancelled:
                    return
                chunk_data = audio_bytes[i : i + _CHUNK_SIZE]
                is_last = i + _CHUNK_SIZE >= total
                yield AudioChunk(seq=seq, data=chunk_data, format=self._fmt, is_last=is_last)
                seq += 1

            if seq == 0:
                yield AudioChunk(seq=0, data=audio_bytes, format=self._fmt, is_last=True)


def _parse_mimo_response(raw: bytes) -> bytes:
    """Parse MiMo chat/completions response to extract audio bytes.

    MiMo returns an OpenAI-compatible chat completion with audio in the
    response.  We try both SSE-style and JSON formats.
    """
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        return b""

    # SSE-style (data: ... lines)
    if text.startswith("data:"):
        lines = text.split("\n")
        for line in lines:
            if not line.startswith("data:"):
                continue
            data_str = line[5:].strip()
            if data_str == "[DONE]":
                break
            try:
                data = json.loads(data_str)
                audio = _extract_audio_from_chunk(data)
                if audio:
                    return audio
            except json.JSONDecodeError:
                continue
        return b""

    # Single JSON body
    try:
        data = json.loads(text)
        return _extract_audio_from_chunk(data)
    except json.JSONDecodeError:
        logger.warning("mimo_unparseable_response", preview=text[:200])
        return b""


def _extract_audio_from_chunk(data: dict) -> bytes:
    """Extract audio bytes from a MiMo response chunk."""
    return (
        _extract_choices_audio(data)
        or _extract_audio_obj(data)
        or _extract_inner_data_audio(data)
        or b""
    )


def _extract_choices_audio(data: dict) -> bytes | None:
    choices = data.get("choices", [])
    if not choices:
        return None
    message = choices[0].get("message") or choices[0].get("delta") or {}
    audio_obj = message.get("audio") or {}
    if isinstance(audio_obj, dict) and "data" in audio_obj:
        return _decode_audio_data(audio_obj["data"])
    return None


def _extract_audio_obj(data: dict) -> bytes | None:
    audio = data.get("audio") or {}
    if isinstance(audio, dict) and "data" in audio:
        return _decode_audio_data(audio["data"])
    return None


def _extract_inner_data_audio(data: dict) -> bytes | None:
    inner = data.get("data") or {}
    if isinstance(inner, dict) and "audio" in inner:
        return _decode_audio_data(inner["audio"])
    return None


def _decode_audio_data(raw: str | bytes) -> bytes:
    if isinstance(raw, str):
        return base64.b64decode(raw)
    if isinstance(raw, bytes):
        return base64.b64decode(raw)
    return b""


class MiMoProvider:
    """MiMo TTS Provider (mimo-v2.5-tts-voicedesign).

    Uses natural-language voice descriptions to create character-specific
    voices.  Accepts a character_id to select the matching voice description.
    """

    def __init__(self, api_key: str, base_url: str = "https://api.xiaomimimo.com/v1"):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=60.0)

    def _build_body(self, req: TTSRequest, character_id: str, stream: bool = False) -> dict:
        emotion = req.emotion if req.emotion in _VALID_EMOTIONS else "neutral"

        voice_desc = _VOICE_DESCRIPTIONS.get(character_id, _VOICE_DESCRIPTIONS["rin"])
        emotion_directive = _EMOTION_DIRECTIVES.get(emotion, "用自然平和的语气")
        user_content = f"{voice_desc} {emotion_directive}"

        emotion_tag = _EMOTION_TAGS.get(emotion, "")
        assistant_content = f"{emotion_tag}{req.text}" if emotion_tag else req.text

        audio_config: dict[str, Any] = {
            "format": "pcm16",
            "optimize_text_preview": False,
        }
        if req.speed != 1.0:
            audio_config["speed"] = req.speed
        if req.pitch != 0:
            audio_config["pitch"] = req.pitch
        if req.volume != 1.0:
            audio_config["volume"] = req.volume

        body: dict[str, Any] = {
            "model": "mimo-v2.5-tts-voicedesign",
            "messages": [
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": assistant_content},
            ],
            "audio": audio_config,
        }
        if stream:
            body["stream"] = True

        return body

    async def synthesize(self, req: TTSRequest, character_id: str = "rin") -> TTSResult:
        """Synthesize speech from text (non-streaming)."""
        body = self._build_body(req, character_id, stream=False)

        try:
            response = await self._client.post(
                f"{self._base_url}/chat/completions",
                json=body,
                headers={
                    "api-key": self._api_key,
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise TTSProviderError(
                f"MiMo API error: {e.response.status_code} - {e.response.text[:500]}",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            raise TTSProviderError(f"MiMo request failed: {str(e)}") from e

        data = response.json()
        audio_bytes = _extract_audio_from_chunk(data)
        if not audio_bytes:
            raise TTSProviderError(f"MiMo response missing audio data: {str(data)[:200]}")

        duration_ms = max(1, len(audio_bytes) * 1000 // (24000 * 2)) if audio_bytes else 0

        return TTSResult(
            audio=audio_bytes,
            format="pcm16",
            duration_ms=duration_ms,
            request_id=str(uuid.uuid4()),
        )

    async def stream_synthesize(self, req: TTSRequest, character_id: str = "rin") -> Any:
        """Synthesize speech from text (streaming).

        Returns a MiMoCancellableStream that chunks the full response.
        """
        body = self._build_body(req, character_id, stream=True)
        response_cm = self._client.stream(
            "POST",
            f"{self._base_url}/chat/completions",
            json=body,
            headers={
                "api-key": self._api_key,
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )
        return MiMoCancellableStream(response_cm, character_id, fmt="pcm16")

    def estimate_cost_cents(self, text: str) -> float:
        """Estimate cost in cents for synthesizing text via MiMo.

        MiMo voicedesign pricing is per-character; approximate at
        ~0.015 CNY/char → ~0.2 US cents per char.
        """
        return len(text) * 0.02

    @property
    def name(self) -> str:
        """Provider name."""
        return "mimo"
