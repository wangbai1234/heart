from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from heart.api.routes_promotions import (
    AdminReviewAction,
    _normalize_url,
    _parse_uuid,
    admin_needs_info,
    admin_reject_promotion,
    submit_promotion,
)
from heart.core.auth import TokenData


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
