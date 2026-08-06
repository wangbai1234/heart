"""Unit: proactive /pending route splits content into bubble segments.

The SS06 proactive message is a single content string in the DB. Regular chat
replies are split into dialog vs action bubbles by ss05_composer.split_response;
proactive messages must get the same treatment so an opening like
"（叹了口气）在忙吗？" renders as a grey action pill + a text bubble instead of
one run-together bubble.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from heart.api.main import create_app
from heart.api.wiring import get_db
from heart.core.auth import TokenData, get_current_user
from heart.ss06_inner_state import proactive_repo


def _make_client(user_id):
    """TestClient app with auth + DB stubbed so no network/DB is touched."""
    app = create_app()

    async def _override_db():
        yield None  # route passes db straight to the stubbed repo

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: TokenData(
        user_id=str(user_id), email="t@e.co"
    )
    return app


def _msg(content: str):
    return SimpleNamespace(
        id=uuid4(),
        character_id="rin",
        content=content,
        trigger_type="scheduled",
        created_at=datetime.now(timezone.utc),
    )


def test_pending_message_is_split_into_segments(monkeypatch):
    user_id = uuid4()
    msg = _msg("（轻轻叹了口气）在忙吗？突然有点想你了。")

    async def _fake_fetch(session, user_id, character_id=None):
        return [msg]

    monkeypatch.setattr(proactive_repo, "fetch_pending", _fake_fetch)
    app = _make_client(user_id)
    with TestClient(app) as client:
        resp = client.get(f"/api/proactive/pending?user_id={user_id}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    segments = data["messages"][0]["segments"]
    # Action bracket becomes its own grey pill; dialog is a separate text bubble.
    assert segments[0] == {"kind": "action", "content": "轻轻叹了口气"}
    assert any(s["kind"] == "text" and "在忙吗" in s["content"] for s in segments)
    # Original content is still present for back-compat / previews.
    assert data["messages"][0]["content"] == msg.content


def test_plain_message_is_single_text_segment(monkeypatch):
    user_id = uuid4()
    msg = _msg("在忙吗？想你了。")

    async def _fake_fetch(session, user_id, character_id=None):
        return [msg]

    monkeypatch.setattr(proactive_repo, "fetch_pending", _fake_fetch)
    app = _make_client(user_id)
    with TestClient(app) as client:
        resp = client.get(f"/api/proactive/pending?user_id={user_id}")

    segments = resp.json()["messages"][0]["segments"]
    assert all(s["kind"] == "text" for s in segments)
    assert "".join(s["content"] for s in segments).replace(" ", "") == "在忙吗？想你了。"
