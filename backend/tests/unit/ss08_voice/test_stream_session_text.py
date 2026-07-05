"""Tests for StreamSession TTS-only text preparation."""

from heart.ss08_voice.stream_session import (
    _extract_tts_stage_directions,
    _strip_tts_stage_directions,
)


def test_round_parentheses_removed_but_square_brackets_preserved():
    text = "（目光停顿片刻）[克制一点]kaito。他们提过一次。"

    stripped, directions = _extract_tts_stage_directions(text)

    assert stripped == "[克制一点]kaito。他们提过一次。"
    assert directions == ["目光停顿片刻"]
    assert _strip_tts_stage_directions(text) == stripped
