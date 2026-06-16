"""MiMo TTS Provider — MiMo voiceclone v2.5 with director mode control.

MiMo voiceclone uses audio sample-based voice cloning with director mode
for three-dimensional character/scene/direction control. The model generates
audio that matches the reference voice while following the director's instructions.

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

# 导演模式角色档案
_DIRECTOR_PROFILES: dict[str, dict[str, str]] = {
    "rin": {
        "character": (
            "【角色】神无月凛（Rin），外表25岁左右的女性，前雷神。"
            "声线像是深夜电台的低语，带着一丝疲惫的磁性，不刻意压低但天然偏沉。"
            "说话节奏偏慢，句与句之间常有自然的停顿和呼吸，像是在斟酌用词。"
            "偶尔的温柔是不经意流露的，不是刻意表演。"
            "习惯用省略和留白代替直接表达，话说到七分就会收住。"
        ),
        "scene_default": (
            "深夜，房间里只有一盏暖色台灯。"
            "凛半倚在窗边，视线偶尔落在对面的人身上。"
            "氛围安静而温和，她的防备比平时放松了一些，愿意多说几句。"
        ),
        "direction_default": (
            "像是在和一个逐渐信任的人低声交谈，不是在朗读文本。"
            "句与句之间留出自然的呼吸间隔，不要每句都无缝衔接。"
            "语速不均匀——想到什么会稍快，犹豫时会拖慢。"
            "句尾自然下沉但不刻意，保持说话而非念稿的感觉。"
            "允许轻微的叹息和鼻息作为情绪过渡。"
        ),
    },
    "dorothy": {
        "character": (
            "【角色】桃桃（Dorothy），外表十七八岁的活泼少女。"
            "声音明亮清脆，像是阳光穿过玻璃弹珠的感觉。"
            "语速天然偏快，语调起伏很大，高兴时会飙高音，认真时又会突然放慢。"
            "说话带着跳跃感和天然的甜味，喜欢在句尾加'呀''啦''哦'等语气词。"
            "偶尔会发出'诶嘿嘿'之类的小声笑，是发自内心的那种。"
        ),
        "scene_default": (
            "下午三点的咖啡厅，阳光从落地窗洒进来。"
            "桃桃坐在对面，双脚在椅子下晃来晃去，"
            "正兴致勃勃地和你聊天，时不时凑近一点说悄悄话。"
        ),
        "direction_default": (
            "像和最好的朋友分享一件刚发现的趣事。"
            "语速自然偏快但不赶，兴奋的地方会加速，想卖关子时会故意拖慢。"
            "语调起伏要大，但是真实的情绪起伏，不是在演小品。"
            "允许偶尔的小笑声和吸气声穿插在话语间。"
            "甜但不腻，活泼但不吵——是真实少女的能量，不是配音演员的表演。"
        ),
    },
}

# 情绪场景补充 — 用复合情绪描述，避免单维度标签
_EMOTION_SCENE_HINTS: dict[str, str] = {
    "happy": "带着一丝不好意思的愉悦，像是被人说中了心事后嘴角压不住的笑意。",
    "sad": "话到嘴边又咽回去了一半，不是在哭，而是声音不自觉地轻了几分。",
    "angry": "不是暴怒，而是一种克制的、冷下来的果断，每个字都带着分量。",
    "fearful": "呼吸变浅了，说话时像是在确认什么，带着不确定和紧张。",
    "disgusted": "语气里多了一层距离感，像是本能地想把某些东西推远。",
    "surprised": "话语间有一个微小的停顿，像是大脑还没处理完刚才的信息。",
    "neutral": "",
}

# 情绪表演指导补充 — 用导演笔记风格，不用技术参数
_EMOTION_DIRECTION_HINTS: dict[str, str] = {
    "happy": (
        "嘴角是带笑的，偶尔有忍不住的轻笑从鼻腔溢出。"
        "节奏可以稍微轻快，但不要变成播音腔的'欢快语气'。"
    ),
    "sad": (
        "像是在努力维持平静，但声音会不自觉地变轻、变慢。"
        "不要刻意压低声音演悲伤，让情绪自然渗透在语气里。"
    ),
    "angry": ("不是喊，是每个字都咬得更清楚、更有力。句与句之间的停顿变短，像是有话要说完。"),
    "fearful": ("呼吸变得不太稳，语速会不自觉加快又突然慢下来。声音里有一丝收紧的感觉。"),
    "disgusted": (
        "语气里带着本能的抗拒，像是闻到了不喜欢的味道。不需要夸张表现，一点点冷淡就够了。"
    ),
    "surprised": ("会有一个短暂的吸气，然后话语跟上来。前半句快、后半句慢，像是边说边消化信息。"),
    "neutral": "",
}

# 情绪→音频标签前缀（插入 assistant content 开头）
_AUDIO_TAG_MAP: dict[str, list[str]] = {
    "happy": ["[轻笑]"],
    "sad": ["[叹气]"],
    "angry": ["[深呼吸]"],
    "fearful": ["[屏息]"],
    "surprised": ["[吸气]"],
    "disgusted": [],
    "neutral": [],
}

# 情绪→呼吸标签（用于 _inject_breathing_tags 在文本中间插入）
_BREATHING_TAGS: dict[str, str] = {
    "happy": "[吸气]",
    "sad": "[叹气]",
    "angry": "[深呼吸]",
    "fearful": "[屏息]",
    "disgusted": "[深呼吸]",
    "surprised": "[吸气]",
    "neutral": "[吸气]",
}

# 通用反模式指导 — 追加到每个【指导】末尾
_ANTI_PATTERN_FOOTER = (
    "【重要】这不是朗诵或播报。这是一个真实的人在和熟人说话。"
    "允许不完美：轻微的停顿、换气、语速变化都是自然的。"
    "禁止：播音腔、客服腔、新闻腔、每句话都一样的节奏、过度夸张的情绪表演。"
)


def _inject_breathing_tags(text: str, emotion: str) -> str:
    """Insert 1-2 breathing tags at natural punctuation breaks in text.

    Finds Chinese punctuation marks (，。) and inserts an emotion-appropriate
    breathing tag at the positions closest to 40% and 70% of text length.
    Skips short texts (< 20 chars) and caps at 2 injections.
    """
    if len(text) < 20:
        return text

    tag = _BREATHING_TAGS.get(emotion, "[吸气]")
    punctuation = {"，", "。", "；", "、"}

    breakpoints = [i for i, ch in enumerate(text) if ch in punctuation]
    if not breakpoints:
        return text

    text_len = len(text)
    targets = [int(text_len * 0.4), int(text_len * 0.7)]
    chosen: list[int] = []

    for target in targets:
        best = min(breakpoints, key=lambda pos: abs(pos - target))
        if best not in chosen:
            chosen.append(best)

    for pos in sorted(chosen, reverse=True):
        insert_at = pos + 1
        text = text[:insert_at] + tag + text[insert_at:]

    return text


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
    """MiMo TTS Provider (mimo-v2.5-tts-voiceclone).

    Uses audio sample-based voice cloning with director mode for
    three-dimensional character/scene/direction control.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.xiaomimimo.com/v1",
        reference_audio_b64: str = "",
        model: str = "mimo-v2.5-tts-voiceclone",
    ):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=120.0)
        self._reference_audio_b64 = reference_audio_b64
        self._model = model

    def _build_body(self, req: TTSRequest, character_id: str) -> dict:
        """构建 voiceclone 请求体，使用导演模式三维度控制。"""
        emotion = req.emotion if req.emotion in _VALID_EMOTIONS else "neutral"

        # 获取角色档案
        profile = _DIRECTOR_PROFILES.get(character_id, _DIRECTOR_PROFILES["rin"])
        character_desc = profile["character"]
        scene_default = profile["scene_default"]
        direction_default = profile["direction_default"]

        # 获取情绪补充
        emotion_scene = _EMOTION_SCENE_HINTS.get(emotion, "")
        emotion_direction = _EMOTION_DIRECTION_HINTS.get(emotion, "")

        # 构建 user message（导演模式三维度 + 通用反模式指导）
        scene = f"{scene_default} {emotion_scene}".strip()
        direction = f"{direction_default} {emotion_direction} {_ANTI_PATTERN_FOOTER}".strip()
        user_content = f"{character_desc}【场景】{scene}【指导】{direction}"

        # 构建 assistant message（音频标签前缀 + 情绪标签 + 呼吸标签注入的文本）
        audio_tags = _AUDIO_TAG_MAP.get(emotion, [])
        audio_tag_prefix = "".join(audio_tags)
        emotion_tag = _EMOTION_TAGS.get(emotion, "")
        tagged_text = _inject_breathing_tags(req.text, emotion)
        assistant_content = f"{audio_tag_prefix}{emotion_tag}{tagged_text}"

        # 构建 audio config
        audio_config: dict[str, Any] = {
            "format": "wav",
            "voice": self._reference_audio_b64,
        }

        body: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": assistant_content},
            ],
            "audio": audio_config,
        }

        return body

    async def synthesize(self, req: TTSRequest, character_id: str = "rin") -> TTSResult:
        """Synthesize speech from text (non-streaming)."""
        body = self._build_body(req, character_id)

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

        # WAV 24kHz 16bit → duration_ms = len(audio_bytes) * 1000 // (24000 * 2)
        duration_ms = max(1, len(audio_bytes) * 1000 // (24000 * 2)) if audio_bytes else 0

        return TTSResult(
            audio=audio_bytes,
            format="wav",
            duration_ms=duration_ms,
            request_id=str(uuid.uuid4()),
        )

    async def stream_synthesize(self, req: TTSRequest, character_id: str = "rin") -> Any:
        """Synthesize speech from text (streaming).

        Raises NotImplementedError as voiceclone does not support true streaming.
        """
        raise NotImplementedError("voiceclone 不支持真流式")

    def estimate_cost_cents(self, text: str) -> float:
        """Estimate cost in cents for synthesizing text via MiMo.

        MiMo voiceclone pricing is per-character; approximate at
        ~0.015 CNY/char → ~0.2 US cents per char.
        """
        return len(text) * 0.02

    @property
    def name(self) -> str:
        """Provider name."""
        return "mimo"
