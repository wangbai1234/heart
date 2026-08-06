"""Tests for StreamSession TTS-only text preparation."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from heart.ss08_voice.stream_session import (
    _extract_tts_stage_directions,
    _strip_tts_stage_directions,
)


def test_action_brackets_stripped_but_instruction_kept():
    """TTS input drops （）/【】 actions but keeps the [中文指令] namespace.

    Half-width [] is reserved for the Fish S2 instruction the LLM emits at a
    sentence head; it must survive to the provider. The full-width action
    brackets are still removed so descriptions aren't read aloud
    (TEST_REPORT_20260712 §5.4).
    """
    text = "（目光停顿片刻）[克制一点]kaito。他们提过一次。"

    stripped, directions = _extract_tts_stage_directions(text)

    assert stripped == "[克制一点]kaito。他们提过一次。"
    assert directions == ["目光停顿片刻"]
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


def test_leading_close_bracket_eats_orphan_action_head():
    """Tail half of a split （…）action: 「旁白）真话」→ only 真话 is voiced."""
    text = "目光落向别处）你还好吗？"

    stripped, _ = _extract_tts_stage_directions(text)

    # The orphan action text before ） is dropped, not just the bracket char.
    assert stripped == "你还好吗？"


def test_trailing_open_bracket_eats_orphan_action_tail():
    """Head half of a split （…）action: 「真话（旁白」→ only 真话 is voiced."""
    text = "我在呢（他伸手托住你后脑，唇瓣覆上"

    stripped, _ = _extract_tts_stage_directions(text)

    assert stripped == "我在呢"


def test_pure_action_sentence_strips_to_empty():
    """A sentence that is nothing but a （…）action strips to empty (→ skipped)."""
    text = "（他伸手托住你后脑，唇瓣轻轻覆上，温热而克制）"

    stripped, directions = _extract_tts_stage_directions(text)

    assert stripped == ""
    assert directions == ["他伸手托住你后脑，唇瓣轻轻覆上，温热而克制"]


# ---------------------------------------------------------------------------
# StreamSession.tts_provider_name — populated after finish()
# ---------------------------------------------------------------------------


def _make_tts_result(provider_name: str) -> "MagicMock":
    from heart.ss08_voice.types import TTSResult

    return TTSResult(
        audio=b"\x00\x01",
        format="mp3",
        duration_ms=500,
        request_id="req-1",
        provider_name=provider_name,
    )


def _make_voice_service(provider_name: str) -> MagicMock:
    """Return a minimal VoiceService mock that reports the given provider_name."""
    tts_result = _make_tts_result(provider_name)
    req = MagicMock()
    req.format = "mp3"
    req.text = "hello"
    req.voice_id = "v1"
    req.emotion = "neutral"
    req.speed = 1.0
    req.pitch = 0

    director = MagicMock()
    director.derive.return_value = req

    svc = MagicMock()
    svc.director = director
    svc.synthesize_with_fallback = AsyncMock(return_value=tts_result)
    return svc


@pytest.mark.asyncio
async def test_finish_sets_tts_provider_name():
    from heart.ss08_voice.stream_session import StreamSession

    svc = _make_voice_service("mimo")
    session = StreamSession(svc, AsyncMock())

    await session.submit("turn-1", "hello world", None, 0.0, None, "rin")
    await session.finish()

    assert session.audio_produced is True
    assert session.tts_provider_name == "mimo"


@pytest.mark.asyncio
async def test_finish_sets_fallback_provider_name():
    from heart.ss08_voice.stream_session import StreamSession

    svc = _make_voice_service("minimax")
    session = StreamSession(svc, AsyncMock())

    await session.submit("turn-2", "fallback text", None, 0.0, None, "rin")
    await session.finish()

    assert session.tts_provider_name == "minimax"


@pytest.mark.asyncio
async def test_tts_provider_name_empty_before_finish():
    from heart.ss08_voice.stream_session import StreamSession

    svc = _make_voice_service("mimo")
    session = StreamSession(svc, AsyncMock())

    assert session.tts_provider_name == ""


@pytest.mark.asyncio
async def test_each_sentence_streamed_as_its_own_chunk():
    """Sentence pipeline: N sentences → N audio_chunk sends, seq 0..N-1.

    This is the latency win — sentence 1's audio ships before later sentences
    finish synthesizing, instead of one whole-turn chunk at finish().
    """
    from heart.ss08_voice.stream_session import StreamSession

    sends: list[tuple] = []

    async def _capture(turn_id, seq, audio, is_last, fmt):
        sends.append((seq, is_last, fmt))

    svc = _make_voice_service("mimo")
    session = StreamSession(svc, _capture)
    await session.start()
    await session.submit("t1", "第一句。", None, 0.0, None, "rin")
    await session.submit("t1", "第二句。", None, 0.0, None, "rin")
    await session.submit("t1", "第三句。", None, 0.0, None, "rin")
    await session.finish()

    assert [s[0] for s in sends] == [0, 1, 2]  # one chunk per sentence, ordered
    assert all(s[1] is False for s in sends)  # no chunk claims is_last (turn_end does)
    # full_audio accumulates every sentence for persistence.
    assert session.audio_produced is True
    assert len(session.full_audio) > 0
