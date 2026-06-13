"""Per-sentence emotion inference from text content.

VoiceDirector 之前只用 SS03 角色级 VAD 推断 TTS 情绪。问题是 VAD 在
turn 之间变化很小，且默认值落在 (0, 0.3, 0.5) 上，导致 voice_director
始终命中 neutral 规则——所有句子都被读得很平。

这个模块从句子文本本身推断"该用什么情绪说这句话"，作为 voice_director
的首选信号。规则极简（关键词 + 标点 + 重复符），跑在 hot path 上，
不调 LLM。

Returns:
    InferredDelivery(emotion, speed_delta, pitch_delta, confidence)
    confidence 在 [0, 1]，0 表示没把握（fallback 到 vad）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# Valid MiniMax emotion enum
_VALID_EMOTIONS = {
    "happy",
    "sad",
    "angry",
    "fearful",
    "disgusted",
    "surprised",
    "neutral",
}


@dataclass(frozen=True)
class InferredDelivery:
    emotion: str
    speed_delta: float
    pitch_delta: int
    confidence: float  # 0..1


# 关键词到情绪的映射（精挑细选，避免歧义）
_HAPPY_KEYWORDS = (
    "哈哈",
    "嘻嘻",
    "嘿嘿",
    "哇",
    "太棒",
    "好开心",
    "开心",
    "高兴",
    "棒极",
    "真好",
    "喜欢你",
    "爱你",
    "幸福",
    "好玩",
    "有意思",
    "haha",
    "yay",
    "wow",
)
_SAD_KEYWORDS = (
    "好累",
    "累了",
    "难过",
    "伤心",
    "想哭",
    "哭了",
    "孤独",
    "寂寞",
    "失望",
    "心疼",
    "可惜",
    "遗憾",
    "舍不得",
    "对不起",
    "抱歉",
    "唉",
    "哎",
    "叹气",
)
_ANGRY_KEYWORDS = (
    "讨厌",
    "烦",
    "气死",
    "生气",
    "受够",
    "别说了",
    "闭嘴",
    "够了",
    "凭什么",
    "为什么要",
    "不行",
)
_FEARFUL_KEYWORDS = (
    "害怕",
    "怕",
    "担心",
    "紧张",
    "不安",
    "慌",
    "吓",
)
_SURPRISED_KEYWORDS = (
    "真的吗",
    "真的？",
    "什么？",
    "竟然",
    "居然",
    "没想到",
    "天哪",
    "我去",
)
_TENDER_KEYWORDS = (
    # 不是 MiniMax enum 里的，但映射为 "sad"（柔软低沉）效果近似
    "晚安",
    "保重",
    "记得",
    "陪着你",
    "在这里",
    "别怕",
    "没事的",
    "嗯",
)

_ELLIPSIS_RE = re.compile(r"…{1,}|\.{3,}|。{2,}")
_REPEATED_PUNCT_RE = re.compile(r"([！!？?])\1{1,}")


def _contains_any(text: str, words: tuple[str, ...]) -> bool:
    return any(w in text for w in words)


# Keyword → (emotion, speed_delta, pitch_delta, confidence)
_KEYWORD_RULES: tuple[tuple[tuple[str, ...], str, float, int, float], ...] = (
    (_HAPPY_KEYWORDS, "happy", +0.08, +2, 0.9),
    (_ANGRY_KEYWORDS, "angry", +0.10, +2, 0.9),
    (_SAD_KEYWORDS, "sad", -0.15, -2, 0.9),
    (_FEARFUL_KEYWORDS, "fearful", +0.10, +2, 0.85),
    (_SURPRISED_KEYWORDS, "surprised", +0.05, +3, 0.85),
)


def _from_keywords(text: str) -> Optional[InferredDelivery]:
    for words, emo, sp, pi, conf in _KEYWORD_RULES:
        if _contains_any(text, words):
            return InferredDelivery(emo, sp, pi, conf)
    return None


def _from_punctuation(text: str) -> Optional[InferredDelivery]:
    if _REPEATED_PUNCT_RE.search(text):
        if any(p in text for p in ("？", "?")):
            return InferredDelivery("surprised", +0.05, +2, 0.7)
        return InferredDelivery("happy", +0.05, +1, 0.6)
    if text.endswith(("！", "!")):
        return InferredDelivery("happy", +0.03, +1, 0.55)
    if text.endswith(("？", "?")):
        return InferredDelivery("surprised", 0.0, +1, 0.5)
    return None


def infer_emotion_from_text(text: str) -> InferredDelivery:
    """Infer delivery emotion. Priority: keywords > punctuation > soft cues."""
    if not text:
        return InferredDelivery("neutral", 0.0, 0, 0.0)
    t = text.strip()

    kw = _from_keywords(t)
    if kw is not None:
        return kw

    punct = _from_punctuation(t)
    if punct is not None:
        return punct

    if _ELLIPSIS_RE.search(t) or _contains_any(t, _TENDER_KEYWORDS):
        return InferredDelivery("sad", -0.10, -1, 0.6)

    return InferredDelivery("neutral", 0.0, 0, 0.0)


def is_valid_emotion(emotion: Optional[str]) -> bool:
    return emotion in _VALID_EMOTIONS
