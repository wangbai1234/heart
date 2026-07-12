"""Tests for StreamSession TTS-only text preparation."""

from heart.ss08_voice.stream_session import (
    _extract_tts_stage_directions,
    _strip_tts_stage_directions,
)


def test_action_brackets_all_stripped_from_tts_input():
    """TTS input drops every bracket the bubble splitter treats as an action.

    Keeps stream_session aligned with ``message_splitter._ACTION_RE`` so any
    span rendered as a grey action pill in the UI is also skipped by TTS
    (TEST_REPORT_20260712 §5.4).
    """
    text = "（目光停顿片刻）[克制一点]kaito。他们提过一次。"

    stripped, directions = _extract_tts_stage_directions(text)

    assert stripped == "kaito。他们提过一次。"
    assert directions == ["目光停顿片刻", "克制一点"]
    assert _strip_tts_stage_directions(text) == stripped


def test_full_width_action_brackets_stripped():
    text = "【叹气】好吧，我明白了。"

    stripped, directions = _extract_tts_stage_directions(text)

    assert stripped == "好吧，我明白了。"
    assert directions == ["叹气"]


def test_no_brackets_passes_through_untouched():
    text = "你好呀，今天怎么样？"

    stripped, directions = _extract_tts_stage_directions(text)

    assert stripped == "你好呀，今天怎么样？"
    assert directions == []


def test_repeated_brackets_all_removed():
    text = "（笑）你今天真的很好看（歪头）真的哦。"

    stripped, directions = _extract_tts_stage_directions(text)

    assert stripped == "你今天真的很好看真的哦。"
    assert directions == ["笑", "歪头"]
