from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from heart.api.routes_promotions import (
    AdminReviewAction,
    _normalize_url,
    _parse_uuid,
    _pending_membership_rewards,
    admin_approve_promotion,
    admin_needs_info,
    admin_reject_promotion,
    submit_promotion,
)
from heart.core.auth import TokenData


def _mapping_result(row):
    result = MagicMock()
    result.mappings.return_value.first.return_value = row
    return result


def test_normalize_url_trims_whitespace_and_trailing_slashes():
    assert _normalize_url(" https://example.com/post/123/// ") == "https://example.com/post/123"


def test_parse_uuid_rejects_invalid_external_id():
    with pytest.raises(HTTPException) as exc_info:
        _parse_uuid("not-a-uuid", "submission_id")
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "submission_id 格式无效"


@pytest.mark.asyncio
async def test_submit_rejects_creator_without_post_url_before_db_access():
    db = AsyncMock()
    with pytest.raises(HTTPException) as exc_info:
        await submit_promotion(
            task_type="creator",
            platform="douyin",
            post_url=None,
            source_submission_id=None,
            title=None,
            likes_count=None,
            file=None,
            current_user=TokenData(user_id=str(uuid4())),
            db=db,
        )
    assert exc_info.value.status_code == 422
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("handler", "detail"),
    [
        (admin_reject_promotion, "驳回原因不能为空"),
        (admin_needs_info, "补充说明不能为空"),
    ],
)
async def test_admin_reason_is_required_before_db_access(handler, detail):
    db = AsyncMock()
    with pytest.raises(HTTPException) as exc_info:
        await handler(str(uuid4()), AdminReviewAction(reason="  "), None, db)
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == detail
    db.execute.assert_not_awaited()


@pytest.mark.parametrize(
    ("likes", "granted_300", "granted_1000", "thresholds"),
    [
        (299, False, False, []),
        (300, False, False, [300]),
        (1000, False, False, [300, 1000]),
        (1000, True, False, [1000]),
        (1000, True, True, []),
    ],
)
def test_pending_membership_rewards_are_cumulative_and_idempotent(
    likes, granted_300, granted_1000, thresholds
):
    rewards = _pending_membership_rewards(likes, granted_300, granted_1000)
    assert [reward["threshold"] for reward in rewards] == thresholds


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("likes", "expected_tiers"),
    [
        (299, []),
        (300, ["plus"]),
        (1000, ["plus", "immersive"]),
    ],
)
async def test_admin_likes_approval_reports_granted_memberships(likes, expected_tiers):
    submission_id = uuid4()
    user_id = uuid4()
    row = {
        "id": submission_id,
        "user_id": user_id,
        "task_type": "likes",
        "likes_count": likes,
        "source_submission_id": None,
        "milestone_300_granted": False,
        "milestone_1000_granted": False,
        "status": "pending",
    }
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[_mapping_result(row), *[MagicMock() for _ in expected_tiers], MagicMock()]
    )
    db.commit = AsyncMock()

    with patch("heart.api.routes_promotions.grant_coupon", new=AsyncMock()) as grant_coupon:
        response = await admin_approve_promotion(str(submission_id), None, db)

    assert [reward["tier"] for reward in response["granted_memberships"]] == expected_tiers
    assert grant_coupon.await_count == len(expected_tiers)
    assert [call.args[2] for call in grant_coupon.await_args_list] == expected_tiers
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_admin_likes_approval_only_grants_missing_source_milestone():
    submission_id = uuid4()
    source_id = uuid4()
    user_id = uuid4()
    row = {
        "id": submission_id,
        "user_id": user_id,
        "task_type": "likes",
        "likes_count": 1000,
        "source_submission_id": source_id,
        "milestone_300_granted": False,
        "milestone_1000_granted": False,
        "status": "pending",
    }
    source_row = {
        "milestone_300_granted": True,
        "milestone_1000_granted": False,
    }
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[_mapping_result(row), _mapping_result(source_row), MagicMock(), MagicMock()]
    )
    db.commit = AsyncMock()

    with patch("heart.api.routes_promotions.grant_coupon", new=AsyncMock()) as grant_coupon:
        response = await admin_approve_promotion(str(submission_id), None, db)

    assert [reward["tier"] for reward in response["granted_memberships"]] == ["immersive"]
    grant_coupon.assert_awaited_once_with(
        db,
        user_id,
        "immersive",
        30,
        "promotion_likes_1000",
        f"promotion:{source_id}:likes1000",
    )
