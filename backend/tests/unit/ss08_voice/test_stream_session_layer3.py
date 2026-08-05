"""Layer-3: StreamSession bakes per-sentence [中文指令] from emotion labels."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from heart.ss08_voice.stream_session import StreamSession
from heart.ss08_voice.voice_director import VoiceDirector


def _voice_service_capturing() -> tuple[MagicMock, dict]:
    """VoiceService whose director records the text passed to derive()."""
    captured: dict = {}

    def _derive(*, text, character_id, vad, intimacy, active_emotions, stage_directions):
        captured["text"] = text
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
    director.resolve_s2_instruction.side_effect = VoiceDirector.resolve_s2_instruction

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
async def test_per_sentence_instructions_baked_in_order(monkeypatch):
    # Non-clone voice → per-sentence [中文指令] should be inlined for each label.
    from heart.ss08_voice import voice_catalog as vc

    prof = MagicMock()
    prof.clone_stability = False
    monkeypatch.setattr(vc, "get_voice_profile", lambda cid: prof)

    svc, captured = _voice_service_capturing()
    session = StreamSession(svc, AsyncMock())
    await session.submit("t1", "你来啦。", None, 0.0, None, "rin", emotion_label="轻快")
    await session.submit("t1", "今天怎么没精神？", None, 0.0, None, "rin", emotion_label="关切")
    await session.finish()

    text = captured["text"]
    assert text == "[轻快地说]你来啦。[关切地说]今天怎么没精神？"


@pytest.mark.asyncio
async def test_no_labels_uses_whole_turn_path(monkeypatch):
    # No emotion labels → text-mode behaviour: no injected [中文指令].
    from heart.ss08_voice import voice_catalog as vc

    prof = MagicMock()
    prof.clone_stability = False
    monkeypatch.setattr(vc, "get_voice_profile", lambda cid: prof)

    svc, captured = _voice_service_capturing()
    session = StreamSession(svc, AsyncMock())
    await session.submit("t1", "你来啦。", None, 0.0, None, "rin")
    await session.submit("t1", "今天怎么样？", None, 0.0, None, "rin")
    await session.finish()

    assert captured["text"] == "你来啦。今天怎么样？"


@pytest.mark.asyncio
async def test_clone_voice_skips_per_sentence(monkeypatch):
    # clone_stability voices suppress model-level emotion prefixes (timbre).
    from heart.ss08_voice import voice_catalog as vc

    prof = MagicMock()
    prof.clone_stability = True
    monkeypatch.setattr(vc, "get_voice_profile", lambda cid: prof)

    svc, captured = _voice_service_capturing()
    session = StreamSession(svc, AsyncMock())
    await session.submit("t1", "你来啦。", None, 0.0, None, "rin", emotion_label="轻快")
    await session.finish()

    assert "[轻快地说]" not in captured["text"]
