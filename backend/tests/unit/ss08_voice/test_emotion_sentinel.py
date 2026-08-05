"""Layer-3 instruction stripper: display-path removal of [中文指令] spans."""

from __future__ import annotations

from heart.ss08_voice.emotion_sentinel import InstructionStripper


def test_stripper_removes_inline_complete_span():
    s = InstructionStripper()
    out = s.feed("[关切地说]今天怎么了")
    assert out == "今天怎么了"
    assert s.flush() == ""


def test_stripper_passes_clean_text_through():
    s = InstructionStripper()
    assert s.feed("普通文本") == "普通文本"
    assert s.flush() == ""


def test_stripper_holds_span_across_chunks():
    s = InstructionStripper()
    # [温柔地说] is split across two feeds — no half-marker may leak.
    first = s.feed("好呀[温柔")
    second = s.feed("地说]你好")
    tail = s.flush()
    assert "[" not in first and "]" not in first
    assert "[" not in second and "]" not in second
    assert (first + second + tail) == "好呀你好"


def test_stripper_removes_multiple_spans():
    s = InstructionStripper()
    out = s.feed("[轻快地说]你来啦。[关切地问]怎么了")
    assert out == "你来啦。怎么了"
    assert s.flush() == ""


def test_stripper_flushes_unclosed_bracket():
    # A lone '[' that never closes is surfaced on flush, not swallowed.
    s = InstructionStripper()
    assert s.feed("你好[未闭合") == "你好"
    assert s.flush() == "[未闭合"
