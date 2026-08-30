from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from heart.api.routes_admin import _grant_approval_rewards
from heart.api.routes_characters import _ensure_publishable_quota


def _scalar_result(value):
    result = MagicMock()
    result.scalar.return_value = value
    result.scalar_one_or_none.return_value = value
    return result


@pytest.mark.asyncio
async def test_publishable_quota_rejects_eleventh_active_public_or_unlisted_character():
    db = AsyncMock()
    db.execute.side_effect = [_scalar_result(None), _scalar_result(10)]

    with pytest.raises(HTTPException) as exc_info:
        await _ensure_publishable_quota(db, uuid4())

    assert exc_info.value.status_code == 422
    assert "最多 10 个" in exc_info.value.detail


@pytest.mark.asyncio
async def test_unlisted_approval_grants_no_coins_and_no_milestone():
    db = AsyncMock()
    db.execute.return_value = _scalar_result(4)

    with patch("heart.api.routes_admin.grant", new=AsyncMock()) as grant_mock:
        result = await _grant_approval_rewards(db, "char_link_only", uuid4(), "unlisted")

    grant_mock.assert_not_awaited()
    assert result == {
        "reward_eligible": False,
        "coins_granted": 0,
        "approved_count": 4,
        "milestone_plus_granted": False,
    }


@pytest.mark.asyncio
async def test_public_approval_grants_one_hundred_coins():
    db = AsyncMock()
    db.execute.side_effect = [_scalar_result(None), _scalar_result(1)]
    owner_id = uuid4()

    with patch("heart.api.routes_admin.grant", new=AsyncMock()) as grant_mock:
        result = await _grant_approval_rewards(db, "char_public", owner_id, "public")

    grant_mock.assert_awaited_once_with(
        db,
        owner_id,
        10_000,
        idempotency_key="char_review:char_public",
        type_str="grant",
        ref_type="character_review",
        ref_id="char_public",
    )
    assert result["reward_eligible"] is True
    assert result["coins_granted"] == 100
    assert result["approved_count"] == 1
