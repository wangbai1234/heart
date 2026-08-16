"""Layer-3: orchestrator._stream_compose mid-stream break signalling.

Regression for the "half-bubble" bug: when the LLM stream drops mid-way (e.g.
a failover second-hop relay disconnect) after some content was already
streamed, the turn used to end cleanly and the client was left with a truncated
half-sentence bubble that looked like a real reply. _stream_compose now records
``stream_meta["stream_error"] = True`` so the WS route can surface a retryable
STREAM_INTERRUPTED error even though partial text exists.
"""

from __future__ import annotations

import uuid

import pytest

from heart.ss07_orchestration.models import TurnRequest
from heart.ss07_orchestration.orchestrator import Orchestrator


class _RaisingComposer:
    """Yields a couple of chunks, then breaks mid-stream."""

    def __init__(self, chunks):
        self._chunks = chunks

    async def compose_stream(self, *, ctx, user_message, conversation_history, temperature):
        ctx.stream_meta.setdefault("served_model", "deepseek")
        for c in self._chunks:
            yield c
        raise RuntimeError("relay dropped connection mid-stream")


class _CleanComposer:
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


def _req() -> TurnRequest:
    return TurnRequest(
        user_id=uuid.uuid4(),
        character_id="rin",
        user_message="hi",
        history=[],
        trace_id=uuid.uuid4(),
        voice_enabled=False,
    )


async def _collect(orch, req, composer, meta):
    deltas = []
    async for ev in orch._stream_compose(
        req, composer, uuid.uuid4(), None, 0.0, [], None, meta, voice_enabled=req.voice_enabled
    ):
        if ev["type"] == "text_delta":
            deltas.append(ev["delta"])
    return "".join(deltas)


@pytest.mark.asyncio
async def test_midstream_error_sets_stream_error_flag_but_keeps_partial_text():
    # A break after some content: partial deltas still flow, and the meta dict
    # is flagged so the caller can surface a STREAM_INTERRUPTED retry.
    orch = _orch()
    meta: dict = {}
    composer = _RaisingComposer(["他猛地抬起头，", "猩红的眸子紧紧盯着你，"])
    display = await _collect(orch, _req(), composer, meta)

    assert display == "他猛地抬起头，猩红的眸子紧紧盯着你，"
    assert meta.get("stream_error") is True


@pytest.mark.asyncio
async def test_clean_stream_does_not_set_stream_error_flag():
    orch = _orch()
    meta: dict = {}
    composer = _CleanComposer(["你好呀。", "今天怎么样？"])
    display = await _collect(orch, _req(), composer, meta)

    assert display == "你好呀。今天怎么样？"
    assert meta.get("stream_error", False) is False
