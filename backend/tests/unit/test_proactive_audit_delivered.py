"""Regression: v2 proactive audit rows must be persisted with ``delivered=true``.

In the v2 path the proactive message is *actually* delivered inline via
``chat_messages`` (is_proactive=true). The ``proactive_messages`` row written by
``insert_message_audit`` is a pure audit/dedup record and must NOT be re-served
by ``fetch_pending`` (which returns ``delivered=false`` rows). Writing it as
pending was the root cause of the "角色主动发消息发两条" duplicate: the frontend
rendered the message once from chat history and once again from the /pending
injection.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from heart.ss06_inner_state import proactive_repo
from heart.ss06_inner_state.models import ProactiveMessage


@pytest.mark.unit
async def test_insert_message_audit_marks_delivered_true():
    session = AsyncMock()
    now = datetime.now(timezone.utc)
    msg = ProactiveMessage(
        user_id=uuid4(),
        character_id="char_x",
        content="（望着窗外）在做什么呢",
        trigger_type="proactive_v2_idle",
        created_at=now,
    )

    await proactive_repo.insert_message_audit(session, msg)

    assert session.execute.await_count == 1
    stmt, params = session.execute.await_args.args
    sql = str(stmt).lower()

    # Delivered column is written true, never false — otherwise fetch_pending
    # re-serves an already-delivered message and the client double-renders it.
    assert "delivered_at" in sql
    assert "true" in sql
    assert "false" not in sql
    # delivered_at is bound and non-null (delivery happened at creation time).
    assert params.get("delivered_at") == now
