"""Layer-3 emotion sentinel: parsing + stateful display stripping."""

from __future__ import annotations

from heart.ss08_voice.emotion_sentinel import SentinelStripper, parse_sentence_emotion


def test_head_label_parsed_and_stripped():
    label, text = parse_sentence_emotion("{E:温柔}今天累不累？")
    assert label == "温柔"
    assert text == "今天累不累？"


def test_no_sentinel_returns_none():
    label, text = parse_sentence_emotion("你来啦。")
    assert label is None
    assert text == "你来啦。"


def test_mid_sentence_sentinel_stripped_without_label():
    # Only a head sentinel yields a label; a stray mid one is removed silently.
    label, text = parse_sentence_emotion("你好{E:轻快}呀")
    assert label is None
    assert text == "你好呀"


def test_stripper_holds_sentinel_across_chunks():
    s = SentinelStripper()
    # Sentinel {E:轻快} is split across two feeds — no half-marker may leak.
    first = s.feed("好呀{E:轻")
    second = s.feed("快}你好")
    tail = s.flush()
    assert "{" not in first and "}" not in first
    assert "{" not in second and "}" not in second
    assert (first + second + tail) == "好呀你好"


def test_stripper_passes_clean_text_through():
    s = SentinelStripper()
    assert s.feed("普通文本") == "普通文本"
    assert s.flush() == ""


def test_stripper_removes_inline_complete_sentinel():
    s = SentinelStripper()
    out = s.feed("{E:关切}今天怎么了")
    assert out == "今天怎么了"
    assert s.flush() == ""
