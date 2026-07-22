"""Unit tests for StoryService.process_turn_stream (PR3).

Uses a fake router (deterministic delta stream) and monkeypatched repository so
no DB is required — the focus is the event-frame contract and bubble persistence
wiring, not SQL.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from heart.ss09_story import repository as repo
from heart.ss09_story import service as service_mod
from heart.ss09_story.models import Run, Scenario
from heart.ss09_story.service import StoryService


class _FakeRouter:
    def __init__(self, deltas: list[str] | None = None, raise_after: int | None = None):
        self._deltas = deltas if deltas is not None else ["【旁白】开场。\n", "**林深** 你好。"]
        self._raise_after = raise_after

    async def stream_for(self, model, messages, agent_name="unknown", **kw):
        for i, d in enumerate(self._deltas):
            if self._raise_after is not None and i == self._raise_after:
                raise RuntimeError("boom")
            yield d


class _FakeSession:
    async def commit(self):
        return None


@asynccontextmanager
async def _fake_session_ctx():
    yield _FakeSession()  # repo fns are monkeypatched; only commit() is called


def _fake_factory():
    return _fake_session_ctx()


def _scenario() -> Scenario:
    return Scenario(
        id=uuid4(), slug="s", title="t", genre="悬疑", cover_url=None, blurb="b",
        maturity="all_ages", gm_system_prompt="原文", player_template_json={},
        status="published", is_featured=False, play_count=0,
    )


def _run() -> Run:
    now = datetime.now(timezone.utc)
    return Run(
        id=uuid4(), user_id=uuid4(), scenario_id=uuid4(), player_identity_json={},
        title="t", summary="", summary_watermark=0, turn_count=0, status="active",
        model="deepseek", created_at=now, last_activity_at=now,
    )


@pytest.fixture
def patched_repo(monkeypatch):
    """Stub all repo writes/reads the service touches; record added messages."""
    added: list[dict] = []
    run = _run()

    async def _next_seq(session, run_id):
        return len(added) + 1

    async def _add_message(session, **kw):
        added.append(kw)
        return object()

    async def _bump(session, run_id, **kw):
        return None

    async def _get_run(session, run_id, user_id):
        return run

    async def _recent(session, run_id, limit=16):
        return []

    monkeypatch.setattr(repo, "next_seq", _next_seq)
    monkeypatch.setattr(repo, "add_message", _add_message)
    monkeypatch.setattr(repo, "bump_run_activity", _bump)
    monkeypatch.setattr(repo, "get_run", _get_run)
    monkeypatch.setattr(repo, "recent_messages", _recent)
    return {"added": added, "run": run}


async def _collect(gen):
    return [ev async for ev in gen]


@pytest.mark.asyncio
async def test_turn_stream_happy_path(patched_repo):
    svc = StoryService(_fake_factory, _FakeRouter())
    events = await _collect(
        svc.process_turn_stream(
            run_id=patched_repo["run"].id,
            user_id=patched_repo["run"].user_id,
            player_text="我推门进去。",
            scenario=_scenario(),
        )
    )
    types = [e[0] for e in events]
    assert types[0] == "turn_start"
    assert "text_delta" in types
    assert types[-1] == "turn_end"
    assert events[-1][1]["ok"] is True
    # message_bubble frames for narration + dialogue.
    bubbles = [e[1] for e in events if e[0] == "message_bubble"]
    kinds = [b["kind"] for b in bubbles]
    assert "narration" in kinds and "dialogue" in kinds
    # Player line + each bubble persisted.
    roles = [m["role"] for m in patched_repo["added"]]
    assert "player" in roles
    assert "npc" in roles  # dialogue bubble persisted as npc


@pytest.mark.asyncio
async def test_turn_stream_empty_text_errors(patched_repo):
    svc = StoryService(_fake_factory, _FakeRouter())
    events = await _collect(
        svc.process_turn_stream(
            run_id=patched_repo["run"].id,
            user_id=patched_repo["run"].user_id,
            player_text="   ",
            scenario=_scenario(),
        )
    )
    types = [e[0] for e in events]
    assert types == ["turn_start", "error", "turn_end"]
    assert events[1][1]["code"] == "empty_message"


@pytest.mark.asyncio
async def test_turn_stream_engine_unavailable():
    svc = StoryService(_fake_factory, None)  # no router
    events = await _collect(
        svc.process_turn_stream(
            run_id=uuid4(), user_id=uuid4(), player_text="hi", scenario=_scenario()
        )
    )
    codes = [e[1].get("code") for e in events if e[0] == "error"]
    assert "engine_unavailable" in codes


@pytest.mark.asyncio
async def test_turn_stream_generation_error_before_any_delta(patched_repo):
    svc = StoryService(_fake_factory, _FakeRouter(deltas=["x"], raise_after=0))
    events = await _collect(
        svc.process_turn_stream(
            run_id=patched_repo["run"].id,
            user_id=patched_repo["run"].user_id,
            player_text="我推门进去。",
            scenario=_scenario(),
        )
    )
    codes = [e[1].get("code") for e in events if e[0] == "error"]
    assert "generation_failed" in codes
    assert events[-1][1]["ok"] is False
