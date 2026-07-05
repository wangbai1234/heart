from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from heart.api.routes_chat_ws import RECENT_HISTORY_LIMIT, _load_recent_conversation_history


def test_recent_history_limit_is_50():
    """Short-term window aligned to the commercial spec (最近 50 条)."""
    assert RECENT_HISTORY_LIMIT == 50


@pytest.mark.asyncio
async def test_load_recent_conversation_history_returns_oldest_to_newest_order():
    user_id = uuid.uuid4()
    db = AsyncMock()

    result = MagicMock()
    result.mappings.return_value.all.return_value = [
        {"role": "assistant", "content": "第三句"},
        {"role": "user", "content": "第二句"},
        {"role": "assistant", "content": "第一句"},
    ]
    db.execute.return_value = result

    history = await _load_recent_conversation_history(db, user_id, "rin", limit=3)

    assert history == [
        {"role": "assistant", "content": "第一句"},
        {"role": "user", "content": "第二句"},
        {"role": "assistant", "content": "第三句"},
    ]
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_load_recent_conversation_history_filters_unexpected_roles():
    user_id = uuid.uuid4()
    db = AsyncMock()

    result = MagicMock()
    result.mappings.return_value.all.return_value = [
        {"role": "system", "content": "ignore me"},
        {"role": "user", "content": "保留我"},
    ]
    db.execute.return_value = result

    history = await _load_recent_conversation_history(db, user_id, "rin", limit=2)

    assert history == [{"role": "user", "content": "保留我"}]
