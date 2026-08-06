from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from heart.api.routes_chat_ws import get_inbox_summary
from heart.core.auth import TokenData

_USER = TokenData(user_id="550e8400-e29b-41d4-a716-446655440000", email="t@example.com")


@pytest.mark.asyncio
async def test_inbox_summary_joins_characters_entitlement():
    """Regression: the badge counted unread for characters no longer visible in
    the inbox list (went private / un-approved / disabled / deleted). The query
    must INNER JOIN `characters` with the same predicate list_characters uses so
    the badge total can never exceed what the list can render + clear.
    """
    db = AsyncMock()
    result = MagicMock()
    result.mappings.return_value.all.return_value = []
    db.execute.return_value = result

    await get_inbox_summary(current_user=_USER, db=db)

    db.execute.assert_awaited_once()
    sql = str(db.execute.await_args.args[0]).lower()
    # Entitlement join present…
    assert "join characters" in sql
    assert "c.status = 'active'" in sql
    assert "c.owner_user_id = :uid" in sql
    assert "c.visibility = 'public'" in sql
    assert "c.review_status = 'approved'" in sql


@pytest.mark.asyncio
async def test_inbox_summary_shapes_rows():
    db = AsyncMock()
    result = MagicMock()
    result.mappings.return_value.all.return_value = [
        {
            "character_id": "rin",
            "content": "在想你",
            "modality": "text",
            "created_at": None,
            "unread_count": 3,
        }
    ]
    db.execute.return_value = result

    out = await get_inbox_summary(current_user=_USER, db=db)

    assert out == {
        "items": [
            {
                "character_id": "rin",
                "last_message_text": "在想你",
                "last_message_at": None,
                "modality": "text",
                "unread_count": 3,
            }
        ]
    }
