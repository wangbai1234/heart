"""Resume routing for GET /api/story/runs/{id} (the "剧情消失" fix).

The bug: resuming a long run returned the OLDEST slice of the transcript, so the
recently-played turns were missing until a full reload. The fix routes the
resume default (after_seq=0) to ``recent_transcript`` (newest window) and keeps
``list_messages`` only for explicit forward-pagination (after_seq>0).

No DB: ``get_db`` yields a dummy session and the repo reads are monkeypatched, so
these lock the route's *selection* logic, not the SQL.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from heart.api.main import create_app
from heart.api.wiring import get_db
from heart.core.auth import TokenData, get_current_user
from heart.ss09_story import repository as repo

USER_ID = "550e8400-e29b-41d4-a716-446655440000"
RUN_ID = "11111111-1111-1111-1111-111111111111"


def _fake_run() -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid.UUID(RUN_ID),
        scenario_id=uuid.uuid4(),
        title="t",
        status="active",
        turn_count=3,
        model="deepseek",
        created_at=now,
        last_activity_at=now,
        player_identity_json={},
    )


def _fake_msg(seq: int) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        turn_id=uuid.uuid4(),
        seq=seq,
        role="gm",
        kind="narration",
        npc_name=None,
        content=f"m{seq}",
    )


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    app = create_app()

    async def _fake_db():
        yield object()

    app.dependency_overrides[get_db] = _fake_db
    app.dependency_overrides[get_current_user] = lambda: TokenData(
        user_id=USER_ID, email="t@e.com"
    )

    calls: dict[str, int] = {"recent": 0, "list": 0}

    async def _get_run(session, run_id, user_id):
        return _fake_run()

    async def _recent(session, run_id, limit=400):
        calls["recent"] += 1
        return [_fake_msg(101), _fake_msg(102)]

    async def _list(session, run_id, after_seq=0, limit=200):
        calls["list"] += 1
        return [_fake_msg(after_seq + 1)]

    monkeypatch.setattr(repo, "get_run", _get_run)
    monkeypatch.setattr(repo, "recent_transcript", _recent)
    monkeypatch.setattr(repo, "list_messages", _list)

    yield TestClient(app), calls
    app.dependency_overrides.clear()


def test_resume_default_uses_recent_transcript(client) -> None:
    tc, calls = client
    resp = tc.get(f"/api/story/runs/{RUN_ID}")
    assert resp.status_code == 200, resp.text
    # after_seq=0 → newest window, NOT the oldest slice.
    assert calls == {"recent": 1, "list": 0}
    seqs = [m["seq"] for m in resp.json()["messages"]]
    assert seqs == [101, 102]


def test_forward_pagination_uses_list_messages(client) -> None:
    tc, calls = client
    resp = tc.get(f"/api/story/runs/{RUN_ID}?after_seq=50")
    assert resp.status_code == 200, resp.text
    # after_seq>0 stays forward-pagination scrollback.
    assert calls == {"recent": 0, "list": 1}
    assert resp.json()["messages"][0]["seq"] == 51
