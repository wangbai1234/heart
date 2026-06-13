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
