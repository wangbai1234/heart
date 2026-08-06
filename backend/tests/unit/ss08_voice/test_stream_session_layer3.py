"""Layer-3: StreamSession joins sentences verbatim, keeping inline [中文指令].

The LLM now emits the Fish S2 instruction itself at each sentence head; the
session no longer decorates from an emotion label. Any leading [中文指令]
survives the TTS path (only （）/【】 actions are stripped) and reaches derive().
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from heart.ss08_voice.stream_session import StreamSession


def _voice_service_capturing() -> tuple[MagicMock, dict]:
    """VoiceService whose director records the text of every derive() call.

    Sentence-level pipeline: each sentence is synthesized on its own, so derive()
    fires once per submit(). ``captured["texts"]`` is the per-sentence list;
    ``captured["text"]`` keeps the last for callers that only need one.
    """
    captured: dict = {"texts": []}

    def _derive(*, text, character_id, vad, intimacy, active_emotions, stage_directions):
        captured["text"] = text
        captured["texts"].append(text)
        req = MagicMock()
        req.format = "mp3"
        req.text = text
        req.voice_id = "v1"
        req.emotion = "neutral"
        req.speed = 1.0
        req.pitch = 0
        return req

    director = MagicMock()
    director.derive.side_effect = _derive
    director.emotion_mode = "s2"

    from heart.ss08_voice.types import TTSResult

    svc = MagicMock()
    svc.director = director
    svc.synthesize_with_fallback = AsyncMock(
        return_value=TTSResult(
            audio=b"\x00", format="mp3", duration_ms=1, request_id="r", provider_name="fish"
        )
    )
    return svc, captured


@pytest.mark.asyncio
async def test_inline_instructions_kept_and_joined_in_order():
    # Leading [中文指令] rides inline; segments join verbatim for derive().
    svc, captured = _voice_service_capturing()
    session = StreamSession(svc, AsyncMock())
    await session.start()
    await session.submit("t1", "[轻快地说]你来啦。", None, 0.0, None, "rin")
    await session.submit("t1", "[关切地问]今天怎么没精神？", None, 0.0, None, "rin")
    await session.finish()

    # Each sentence synthesized on its own, in arrival order — inline [中文指令] kept.
    assert captured["texts"] == ["[轻快地说]你来啦。", "[关切地问]今天怎么没精神？"]


@pytest.mark.asyncio
async def test_plain_sentences_pass_through():
    # No instruction brackets → text joined as-is, no injection.
    svc, captured = _voice_service_capturing()
    session = StreamSession(svc, AsyncMock())
    await session.start()
    await session.submit("t1", "你来啦。", None, 0.0, None, "rin")
    await session.submit("t1", "今天怎么样？", None, 0.0, None, "rin")
    await session.finish()

    assert captured["texts"] == ["你来啦。", "今天怎么样？"]


@pytest.mark.asyncio
async def test_action_brackets_stripped_but_instruction_kept():
    # （）actions are removed before TTS; the [中文指令] survives.
    svc, captured = _voice_service_capturing()
    session = StreamSession(svc, AsyncMock())
    await session.start()
    await session.submit("t1", "[温柔地说]你来啦。（侧头看你）今天怎么样？", None, 0.0, None, "rin")
    await session.finish()

    assert captured["text"] == "[温柔地说]你来啦。今天怎么样？"
