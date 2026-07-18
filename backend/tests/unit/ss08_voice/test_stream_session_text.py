"""Tests for StreamSession TTS-only text preparation."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

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
