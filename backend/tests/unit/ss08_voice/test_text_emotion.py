"""Tests for text-based emotion inference."""

import pytest

from heart.ss08_voice.text_emotion import infer_emotion_from_text


@pytest.mark.parametrize(
    "text,expected_emotion",
    [
        ("哈哈太开心了", "happy"),
        ("好累啊，想睡了", "sad"),
        ("讨厌，烦死了", "angry"),
        ("我有点害怕", "fearful"),
        ("真的吗？没想到", "surprised"),
    ],
)
def test_high_confidence_keywords(text, expected_emotion):
    result = infer_emotion_from_text(text)
    assert result.emotion == expected_emotion
    assert result.confidence >= 0.8


def test_ellipsis_yields_sad():
    result = infer_emotion_from_text("嗯…我在")
    assert result.emotion == "sad"
    assert result.confidence > 0


def test_exclamation_yields_happy_with_low_conf():
    result = infer_emotion_from_text("好的!")
    assert result.emotion == "happy"
    assert result.confidence < 0.7  # 不足以覆盖 vad


def test_empty_text_returns_neutral_zero_conf():
    result = infer_emotion_from_text("")
    assert result.emotion == "neutral"
    assert result.confidence == 0.0


def test_plain_text_returns_zero_conf():
    result = infer_emotion_from_text("七月的梅雨季节还要持续七天")
    assert result.emotion == "neutral"
    assert result.confidence == 0.0


def test_speed_pitch_directional():
    """sad 减速降 pitch；happy/angry 加速升 pitch。"""
    sad = infer_emotion_from_text("好累")
    happy = infer_emotion_from_text("哈哈")
    assert sad.speed_delta < 0 and sad.pitch_delta < 0
    assert happy.speed_delta > 0 and happy.pitch_delta > 0


# ── V3: Expanded keyword coverage tests ─────────────────────────────


def test_happy_new_keywords():
    """V3 新增的 happy 关键词应命中（用 >=4 字避免短句衰减）。"""
    for text in ["今天很好呢", "这个挺不错", "感觉还挺挺好", "真是有趣呀", "好好玩儿啊", "好舒服的感觉", "太好了太好了"]:
        result = infer_emotion_from_text(text)
        assert result.emotion == "happy", f"{text!r} should be happy, got {result.emotion}"
        assert result.confidence >= 0.8


def test_sad_new_keywords():
    """V3 新增的 sad 关键词应命中（用 >=4 字避免短句衰减，避开 angry/fearful 关键词）。"""
    for text in ["我有点累了", "感觉好疲惫", "今天好无聊", "有点郁闷了", "今天心情不太好", "状态不太好呀"]:
        result = infer_emotion_from_text(text)
        assert result.emotion == "sad", f"{text!r} should be sad, got {result.emotion}"
        assert result.confidence >= 0.8


def test_warm_keywords_are_neutral_not_sad():
    """晚安/保重/没事的 → neutral (温暖但不悲伤)，避开 fearful/angry 关键词。"""
    for text in ["说晚安了", "你要保重呀", "没事的没事的"]:
        result = infer_emotion_from_text(text)
        assert result.emotion == "neutral", f"{text!r} should be neutral, got {result.emotion}"
        assert result.confidence >= 0.5


def test_tender_keyword_still_sad():
    """真正感伤的 tender 关键词应仍然映射为 sad。"""
    result = infer_emotion_from_text("记得那时候")
    assert result.emotion == "sad"
    assert result.confidence >= 0.5


def test_decide_turn_emotion_threshold_05():
    """标点推断 conf=0.55 应能通过 0.5 阈值（V3 从 0.7 降到 0.5）。"""
    from heart.ss07_orchestration.orchestrator import Orchestrator

    meta = Orchestrator._decide_turn_emotion("今天天气很好呢！", None)
    assert meta["emotion"] == "happy"
