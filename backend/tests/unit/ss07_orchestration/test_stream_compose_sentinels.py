"""Layer-3: orchestrator._stream_compose sentinel handling (voice vs text)."""

from __future__ import annotations

import uuid

import pytest

from heart.ss07_orchestration.models import TurnRequest
from heart.ss07_orchestration.orchestrator import Orchestrator


class _FakeComposer:
    def __init__(self, chunks):
        self._chunks = chunks

    async def compose_stream(self, *, ctx, user_message, conversation_history, temperature):
        ctx.stream_meta.setdefault("served_model", "deepseek")
        for c in self._chunks:
            yield c


def _orch() -> Orchestrator:
    return Orchestrator(
        safety_agent=None,
        composer_builder=None,
        session_manager=None,
        breakers=None,
        safety_event_writer=None,
    )


def _req(voice: bool) -> TurnRequest:
    return TurnRequest(
        user_id=uuid.uuid4(),
        character_id="rin",
        user_message="hi",
        history=[],
        trace_id=uuid.uuid4(),
        voice_enabled=voice,
    )


async def _collect(orch, req, composer):
    deltas, sentences = [], []
    async for ev in orch._stream_compose(
        req, composer, uuid.uuid4(), None, 0.0, [], None, {}, voice_enabled=req.voice_enabled
    ):
        if ev["type"] == "text_delta":
            deltas.append(ev["delta"])
        elif ev["type"] == "sentence":
            sentences.append((ev["text"], ev.get("emotion_label")))
    return "".join(deltas), sentences


@pytest.mark.asyncio
async def test_text_mode_passes_sentinels_through_untouched():
    # Text turns never carry sentinels; even if one appeared, the stripper is
    # off, so the delta stream is byte-identical to the composer output.
    orch = _orch()
    composer = _FakeComposer(["你好呀。", "今天怎么样？"])
    display, _ = await _collect(orch, _req(voice=False), composer)
    assert display == "你好呀。今天怎么样？"


@pytest.mark.asyncio
async def test_voice_mode_strips_display_and_labels_sentences():
    orch = _orch()
    # Sentinel split across chunks on the display path; head-label on TTS path.
    composer = _FakeComposer(["{E:轻快}你好呀。{E:关", "切}今天怎么样？"])
    display, sentences = await _collect(orch, _req(voice=True), composer)
    assert "{" not in display and "}" not in display
    assert display == "你好呀。今天怎么样？"
    labels = [lbl for _, lbl in sentences]
    assert "轻快" in labels and "关切" in labels
    for text, _ in sentences:
        assert "{" not in text
