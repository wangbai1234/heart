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
    # Built-in characters
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
    # Preset voice profiles — keyed by preset_voices.voice_id so user-created
    # characters that select a MiMo preset get the correct voice description.
    "mimo_female_gentle": (
        "一位22岁左右的温柔女性，音色细腻柔和，语调平缓温暖。"
        "语速偏慢（0.9倍速），咬字轻柔，像在轻声安慰身边的朋友。"
        "情绪基调温柔体贴，音质清澈不尖锐，共鸣位置居中。"
    ),
    "mimo_female_cool": (
        "一位28岁左右的成熟御姐，音色低沉有磁性，自信从容，略带慵懒气质。"
        "语速适中（1.0倍速），咬字清晰有力，情绪沉稳克制，不轻易外露。"
        "音质饱满圆润，共鸣位置靠后，带有成熟女性的气场。"
    ),
    "mimo_female_bright": (
        "一位18岁左右的活泼少女，音色明亮甜美，充满青春活力。"
        "语速稍快（1.05倍速），带有少女的轻快跳跃感，情绪阳光开朗。"
        "音质清脆不刺耳，共鸣位置靠前靠上，天真烂漫不做作。"
    ),
    "mimo_female_elegant": (
        "一位30岁左右的知性女性，音色沉静优雅，字字珠玑，思维清晰。"
        "语速偏慢（0.88倍速），停顿恰当，像在娓娓道来一个深思熟虑的答案。"
        "情绪内敛克制，音质温润不浮躁，气质如书卷般沉稳。"
    ),
    "mimo_female_shy": (
        "一位20岁左右的内敛女生，音色清澈纯净，略带羞涩与拘谨。"
        "语速偏慢（0.92倍速），音量偏轻，偶有轻微停顿，像鼓起勇气开口说话。"
        "情绪细腻敏感，音质清透，共鸣位置靠前，带有少女的纯真感。"
    ),
    "mimo_male_gentle": (
        "一位25岁左右的温柔男性，音色温暖细腻，低沉而不压抑。"
        "语速偏慢（0.92倍速），情绪体贴耐心，像在认真倾听并给予回应。"
        "音质浑厚温润，共鸣位置居中，不霸道，像春风般令人放松。"
    ),
    "mimo_male_cool": (
        "一位27岁左右的清冷男性，音色低沉疏离，言辞简练，带有冷峻气质。"
        "语速适中偏慢（0.95倍速），情绪克制内敛，不轻易表达感情。"
        "音质深沉有力，共鸣位置靠后，像深夜的低语，令人着迷。"
    ),
    "mimo_male_energetic": (
        "一位20岁左右的阳光男生，音色明亮爽朗，充满青春活力。"
        "语速稍快（1.05倍速），情绪开朗热情，喜欢用语气词增加亲切感。"
        "音质清亮不刺耳，共鸣位置居中靠前，像大男孩般爽朗自在。"
    ),
    "mimo_male_mature": (
        "一位35岁左右的成熟男性，音色低沉磁性，稳重从容，带有岁月沉淀的厚重感。"
        "语速偏慢（0.9倍速），情绪沉稳大气，每一句话都带有分量感。"
        "音质饱满深沉，共鸣位置靠后靠下，像一位经验丰富的长者在娓娓而谈。"
    ),
    "mimo_male_sweet": (
        "一位23岁左右的软糯暖男，音色温软甜糯，带有亲昵感和撒娇气质。"
        "语速适中（0.97倍速），情绪暖心黏人，偏爱温柔的上扬语调。"
        "音质轻柔不沉闷，共鸣位置靠前，像棉花糖般令人感到被包裹的温暖。"
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

_CHUNK_SIZE = 48000  # ~1 second @ 24 kHz PCM16 — larger chunks reduce decode frequency


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
        # handle → "data:<mime>;base64,..." for zero-shot clone references, so a
        # multi-MB sample is read + encoded once per process, not per turn.
        self._ref_cache: dict[str, str] = {}

    async def _reference_data_uri(self, handle: str) -> str | None:
        """Load a clone reference (local path or http URL) as a data: URI.

        MiMo voiceclone is zero-shot — the reference audio IS the timbre and must
        ride along on every synth call. Returns None (→ caller degrades to
        voicedesign) if the handle can't be loaded.
        """
        if not handle:
            return None
        cached = self._ref_cache.get(handle)
        if cached:
            return cached
        try:
            if handle.startswith("s3://"):
                # Backend-owned object — read with credentials, so a private
                # bucket works (no public-read ACL / presign needed). This is how
                # UGC MiMo clones are staged (see routes_voice._stage_audio_for_clone).
                from heart.infra.storage import get_s3_object

                data, ctype = await get_s3_object(handle[len("s3://") :])
                mime = (ctype or "audio/wav").split(";")[0].strip()
                if mime not in ("audio/mpeg", "audio/mp3", "audio/wav"):
                    mime = "audio/wav"
            elif handle.startswith(("http://", "https://")):
                resp = await self._client.get(handle)
                resp.raise_for_status()
                data = resp.content
                mime = resp.headers.get("content-type", "audio/wav").split(";")[0].strip()
                if mime not in ("audio/mpeg", "audio/mp3", "audio/wav"):
                    mime = "audio/wav"
            else:
                path = handle[len("file://") :] if handle.startswith("file://") else handle
                with open(path, "rb") as f:
                    data = f.read()
                mime = "audio/mpeg" if path.lower().endswith(".mp3") else "audio/wav"
        except Exception as e:
            logger.warning("mimo_reference_load_failed", handle=handle[:80], error=str(e))
            return None

        uri = f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
        self._ref_cache[handle] = uri
        return uri

    def _build_body(
        self,
        req: TTSRequest,
        character_id: str,
        stream: bool = False,
        reference_data_uri: str | None = None,
    ) -> dict:
        emotion = req.emotion if req.emotion in _VALID_EMOTIONS else "neutral"
        emotion_tag = _EMOTION_TAGS.get(emotion, "")
        assistant_content = f"{emotion_tag}{req.text}" if emotion_tag else req.text

        audio_config: dict[str, Any] = {"format": "pcm16"}
        if req.speed != 1.0:
            audio_config["speed"] = req.speed
        if req.pitch != 0:
            audio_config["pitch"] = req.pitch
        if req.volume != 1.0:
            audio_config["volume"] = req.volume

        if reference_data_uri:
            # Zero-shot voice clone: reference audio in audio.voice, text spoken
            # by the assistant message (per MiMo voiceclone spec). NOTE:
            # optimize_text_preview is voicedesign-only — MiMo rejects it on the
            # voiceclone model (400 Param Incorrect), so it must NOT be set here.
            audio_config["voice"] = reference_data_uri
            body: dict[str, Any] = {
                "model": "mimo-v2.5-tts-voiceclone",
                "messages": [
                    {"role": "user", "content": ""},
                    {"role": "assistant", "content": assistant_content},
                ],
                "audio": audio_config,
            }
        else:
            # voicedesign: natural-language voice description drives the timbre.
            audio_config["optimize_text_preview"] = False
            voice_desc = (
                _VOICE_DESCRIPTIONS.get(character_id)
                or _VOICE_DESCRIPTIONS.get(req.voice_id)
                or _VOICE_DESCRIPTIONS["rin"]
            )
            emotion_directive = _EMOTION_DIRECTIVES.get(emotion, "用自然平和的语气")
            body = {
                "model": "mimo-v2.5-tts-voicedesign",
                "messages": [
                    {"role": "user", "content": f"{voice_desc} {emotion_directive}"},
                    {"role": "assistant", "content": assistant_content},
                ],
                "audio": audio_config,
            }
        if stream:
            body["stream"] = True

        return body

    async def synthesize(self, req: TTSRequest, character_id: str = "rin") -> TTSResult:
        """Synthesize speech from text (non-streaming)."""
        reference = (
            await self._reference_data_uri(req.clone_reference) if req.clone_reference else None
        )
        body = self._build_body(req, character_id, stream=False, reference_data_uri=reference)

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
        reference = (
            await self._reference_data_uri(req.clone_reference) if req.clone_reference else None
        )
        body = self._build_body(req, character_id, stream=True, reference_data_uri=reference)
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
