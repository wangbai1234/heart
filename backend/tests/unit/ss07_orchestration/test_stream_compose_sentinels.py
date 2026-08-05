"""Layer-3: orchestrator._stream_compose [中文指令] handling (voice vs text)."""

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
            sentences.append(ev["text"])
    return "".join(deltas), sentences


@pytest.mark.asyncio
async def test_text_mode_passes_through_untouched():
    # Text turns have no instruction spans and the stripper is off, so the
    # delta stream is byte-identical to the composer output.
    orch = _orch()
    composer = _FakeComposer(["你好呀。", "今天怎么样？"])
    display, _ = await _collect(orch, _req(voice=False), composer)
    assert display == "你好呀。今天怎么样？"


@pytest.mark.asyncio
async def test_voice_mode_strips_instruction_from_display_keeps_it_on_tts():
    orch = _orch()
    # [中文指令] split across chunks on the display path; kept raw on TTS path.
    composer = _FakeComposer(["[轻快地说]你好呀。[关", "切地问]今天怎么样？"])
    display, sentences = await _collect(orch, _req(voice=True), composer)

    # Display: brackets fully stripped, no half-marker leaks.
    assert "[" not in display and "]" not in display
    assert display == "你好呀。今天怎么样？"

    # TTS: the instruction survives verbatim on the sentence events.
    joined = "".join(sentences)
    assert "[轻快地说]" in joined
    assert "[关切地问]" in joined
