"""Account-targeted one-off notice routing."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


def _result(*, mapping=None, first=None):
    result = MagicMock()
    result.mappings.return_value.first.return_value = mapping
    result.first.return_value = first
    return result


@pytest.mark.asyncio
async def test_targeted_notice_is_returned():
    from heart.api.routes_notices import get_active_notice

    uid = uuid.uuid4()
    db = AsyncMock()
    db.execute.return_value = _result(
        mapping={
            "id": "vip-thanks-1",
            "eyebrow": "给知眠宝宝",
            "title": "一份专属的感谢",
            "summary": "会员已升级",
            "content": "谢谢你愿意继续相信 yuoyuo。",
            "confirm_label": "谢谢 yuoyuo，我收到了",
            "qr_image_url": None,
            "starts_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            "ends_at": None,
        }
    )
    token = MagicMock(user_id=str(uid))

    response = await get_active_notice(current_user=token, db=db)

    assert response["notice"]["id"] == "vip-thanks-1"
    assert response["notice"]["confirm_label"] == "谢谢 yuoyuo，我收到了"
    assert db.execute.await_count == 1


@pytest.mark.asyncio
async def test_no_targeted_notice_returns_none():
    from heart.api.routes_notices import get_active_notice

    db = AsyncMock()
    db.execute.return_value = _result(mapping=None)
    token = MagicMock(user_id=str(uuid.uuid4()))

    response = await get_active_notice(current_user=token, db=db)

    assert response == {"notice": None}
    assert db.execute.await_count == 1


@pytest.mark.asyncio
async def test_ack_rejects_another_users_targeted_notice():
    from fastapi import HTTPException

    from heart.api.routes_notices import acknowledge_notice

    db = AsyncMock()
    db.execute.return_value = _result(first=None)
    token = MagicMock(user_id=str(uuid.uuid4()))

    with pytest.raises(HTTPException) as exc:
        await acknowledge_notice(notice_id="vip-thanks-other", current_user=token, db=db)

    assert exc.value.status_code == 404
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_ack_targeted_notice_is_idempotent():
    from heart.api.routes_notices import acknowledge_notice

    db = AsyncMock()
    db.execute.side_effect = [_result(first=(1,)), _result()]
    token = MagicMock(user_id=str(uuid.uuid4()))

    response = await acknowledge_notice(
        notice_id="vip-thanks-owned", current_user=token, db=db
    )

    assert response == {"ok": True}
    db.commit.assert_awaited_once()
