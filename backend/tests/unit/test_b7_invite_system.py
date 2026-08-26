"""B7 unit tests: invite codes, signup recording, first-chat rewards."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── mock helpers ──────────────────────────────────────────────────────────────


def _mapping_result(row_dict):
    """Sync result with .mappings().fetchone() → row_dict."""
    mapping = MagicMock()
    mapping.fetchone.return_value = row_dict
    r = MagicMock()
    r.mappings.return_value = mapping
    return r


def _empty_mapping_result():
    mapping = MagicMock()
    mapping.fetchone.return_value = None
    r = MagicMock()
    r.mappings.return_value = mapping
    return r


def _fetchone_result(row):
    """Sync result with .fetchone() → row (tuple or None)."""
    r = MagicMock()
    r.fetchone.return_value = row
    return r


def _scalar_result(value):
    r = MagicMock()
    r.scalar_one.return_value = value
    return r


def _one_mapping_result(row_dict):
    mapping = MagicMock()
    mapping.one.return_value = row_dict
    r = MagicMock()
    r.mappings.return_value = mapping
    return r


def _first_mapping_result(row_dict):
    mapping = MagicMock()
    mapping.first.return_value = row_dict
    r = MagicMock()
    r.mappings.return_value = mapping
    return r


def _mock_db(*side_effects) -> AsyncMock:
    db = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(side_effect=list(side_effects))
    return db


# ── get_or_create_code ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_or_create_code_returns_existing():
    from heart.invite.service import get_or_create_code

    db = _mock_db(_mapping_result({"code": "EXISTING1"}))
    code = await get_or_create_code(db, uuid.uuid4())

    assert code == "EXISTING1"
    assert db.execute.await_count == 1  # only one SELECT, no INSERT


@pytest.mark.asyncio
async def test_get_or_create_code_creates_new():
    from heart.invite.service import get_or_create_code

    db = _mock_db(
        _empty_mapping_result(),  # first SELECT: nothing
        MagicMock(),  # INSERT
        _mapping_result({"code": "NEWCDE42"}),  # second SELECT
    )
    code = await get_or_create_code(db, uuid.uuid4())

    assert code == "NEWCDE42"
    assert db.execute.await_count == 3


@pytest.mark.asyncio
async def test_get_or_create_code_is_8_chars():
    from heart.invite.service import _CODE_LEN, _gen_code

    for _ in range(20):
        code = _gen_code()
        assert len(code) == _CODE_LEN
        assert code.isalnum()
        assert code == code.upper()


# ── record_invite_signup ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_record_invite_signup_unknown_code_returns_invalid_code():
    from heart.invite.service import record_invite_signup

    db = _mock_db(_empty_mapping_result())
    result = await record_invite_signup(db, uuid.uuid4(), "NOTEXIST")

    assert result == "invalid_code"
    assert db.execute.await_count == 1  # only SELECT


@pytest.mark.asyncio
async def test_record_invite_signup_self_invite_returns_self_invite():
    from heart.invite.service import record_invite_signup

    user_id = uuid.uuid4()
    db = _mock_db(_mapping_result({"user_id": user_id}))
    result = await record_invite_signup(db, user_id, "SELFCODE")

    assert result == "self_invite"


@pytest.mark.asyncio
async def test_record_invite_signup_already_bound_returns_already_bound():
    from heart.invite.service import record_invite_signup

    inviter_id = uuid.uuid4()
    # SELECT inviter → found; SELECT existing use → found (already bound)
    db = _mock_db(
        _mapping_result({"user_id": inviter_id}),
        _fetchone_result((99,)),  # existing binding exists
    )
    result = await record_invite_signup(db, uuid.uuid4(), "GOODCODE")

    assert result == "already_bound"
    assert db.execute.await_count == 2


@pytest.mark.asyncio
async def test_record_invite_signup_valid_returns_ok():
    from heart.invite.service import record_invite_signup

    inviter_id = uuid.uuid4()
    db = _mock_db(
        _mapping_result({"user_id": inviter_id}),  # SELECT inviter
        _fetchone_result(None),  # SELECT existing → not bound
        _scalar_result({}),  # runtime invite config → defaults
        _scalar_result(True),  # within binding window, unpaid
        _fetchone_result((123,)),  # INSERT
    )
    with patch("heart.invite.risk.score_binding", new_callable=AsyncMock):
        result = await record_invite_signup(db, uuid.uuid4(), "GOODCODE")

    assert result == "ok"
    assert db.execute.await_count == 5


# ── invite qualification progress ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_handle_invite_progress_no_invite_record_skips():
    from heart.invite.service import handle_invite_progress

    db = _mock_db(_empty_mapping_result())
    await handle_invite_progress(db, uuid.uuid4(), uuid.uuid4(), "真实消息")
    assert db.execute.await_count == 1


@pytest.mark.asyncio
async def test_handle_invite_progress_ignores_emoji_only_message():
    from heart.invite.service import handle_invite_progress

    db = _mock_db()
    await handle_invite_progress(db, uuid.uuid4(), uuid.uuid4(), "  !!! ")
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_invite_progress_qualifies_at_boundary():
    from heart.invite.service import handle_invite_progress

    now = datetime.now(tz=timezone.utc)
    inviter_id = uuid.uuid4()
    invitee_id = uuid.uuid4()
    use_id = 7
    db = _mock_db(
        _mapping_result(
            {
                "id": use_id,
                "inviter_id": inviter_id,
                "risk_level": "low",
                "created_at": now - timedelta(minutes=5),
                "user_created_at": now - timedelta(minutes=5),
                "age_verified_at": now,
            }
        ),
        _scalar_result({}),
        _fetchone_result((101,)),
        _one_mapping_result(
            {
                "msg_count": 3,
                "ai_reply_count": 3,
                "valid_char_count": 15,
                "distinct_message_count": 2,
                "first_msg_at": now - timedelta(seconds=120),
                "last_msg_at": now,
            }
        ),
        MagicMock(),
        _fetchone_result((inviter_id, "low")),
    )

    with (
        patch(
            "heart.invite.service._grant_chance", new_callable=AsyncMock, return_value=True
        ) as grant_chance,
        patch("heart.commission.service.backfill_commissions_for_invitee", new_callable=AsyncMock),
    ):
        await handle_invite_progress(db, invitee_id, uuid.uuid4(), "这是第三条有效消息")

    grant_chance.assert_awaited_once_with(db, inviter_id, use_id)


@pytest.mark.asyncio
async def test_handle_invite_progress_ignores_removed_gates():
    """Short, unverified chats still qualify once volume thresholds are met."""
    from heart.invite.service import handle_invite_progress

    now = datetime.now(tz=timezone.utc)
    inviter_id = uuid.uuid4()
    invitee_id = uuid.uuid4()
    db = _mock_db(
        _mapping_result(
            {
                "id": 8,
                "inviter_id": inviter_id,
                "risk_level": "low",
                "created_at": now - timedelta(days=30),
                "user_created_at": now - timedelta(days=30),
                "age_verified_at": None,
            }
        ),
        _scalar_result({}),
        _fetchone_result((202,)),
        _one_mapping_result(
            {
                "msg_count": 3,
                "ai_reply_count": 0,
                "valid_char_count": 15,
                "distinct_message_count": 2,
                "first_msg_at": now,
                "last_msg_at": now,
            }
        ),
        MagicMock(),
        _fetchone_result((inviter_id, "low")),
    )

    with (
        patch(
            "heart.invite.service._grant_chance", new_callable=AsyncMock, return_value=True
        ) as grant_chance,
        patch("heart.commission.service.backfill_commissions_for_invitee", new_callable=AsyncMock),
    ):
        await handle_invite_progress(db, invitee_id, uuid.uuid4(), "第三条有效消息")

    grant_chance.assert_awaited_once_with(db, inviter_id, 8)


@pytest.mark.asyncio
async def test_handle_invite_progress_duplicate_turn_is_idempotent():
    from heart.invite.service import handle_invite_progress

    now = datetime.now(tz=timezone.utc)
    inviter_id = uuid.uuid4()
    invitee_id = uuid.uuid4()
    db = _mock_db(
        _mapping_result(
            {
                "id": 15,
                "inviter_id": inviter_id,
                "risk_level": "low",
                "created_at": now,
                "user_created_at": now,
                "age_verified_at": now,
            }
        ),
        _scalar_result({}),
        _fetchone_result(None),
    )
    with patch("heart.invite.service._grant_chance", new_callable=AsyncMock) as grant_chance:
        await handle_invite_progress(db, invitee_id, uuid.uuid4(), "重复提交的有效消息")
    grant_chance.assert_not_awaited()
    assert db.execute.await_count == 3


@pytest.mark.asyncio
async def test_grant_chance_respects_daily_limit():
    from heart.invite.service import _grant_chance

    pool = _first_mapping_result({"id": 1, "total_chances": 10000})
    db = _mock_db(
        _scalar_result({}),
        MagicMock(),
        pool,
        _scalar_result(100),
        _scalar_result(5),
        MagicMock(),
    )
    with patch("heart.membership.get_effective_tier", new_callable=AsyncMock, return_value="free"):
        granted = await _grant_chance(db, uuid.uuid4(), 99)
    assert granted is False
    assert db.execute.await_count == 6


# ── GET /api/invite endpoint ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_invite_endpoint_returns_code_and_url():
    from heart.api.routes_invite import get_invite_info

    user_id = uuid.uuid4()
    mock_user = MagicMock()
    mock_user.user_id = str(user_id)
    mock_db = AsyncMock()

    with patch(
        "heart.api.routes_invite.get_or_create_code",
        new_callable=AsyncMock,
        return_value="ABCD1234",
    ):
        result = await get_invite_info(current_user=mock_user, db=mock_db)

    assert result["code"] == "ABCD1234"
    assert "ABCD1234" in result["url"]
    assert "yuoyuo.app" in result["url"]


@pytest.mark.asyncio
async def test_use_invite_code_accepts_valid():
    from heart.api.routes_invite import UseInviteRequest, use_invite_code

    mock_user = MagicMock()
    mock_user.user_id = str(uuid.uuid4())
    mock_db = AsyncMock()
    mock_request = MagicMock()
    mock_request.headers = {}
    mock_request.client = None

    with patch(
        "heart.api.routes_invite.record_invite_signup", new_callable=AsyncMock, return_value="ok"
    ):
        result = await use_invite_code(
            body=UseInviteRequest(code="GOODCODE"),
            request=mock_request,
            current_user=mock_user,
            db=mock_db,
        )

    assert result["accepted"] is True


@pytest.mark.asyncio
async def test_use_invite_code_rejects_too_long():
    from fastapi import HTTPException

    from heart.api.routes_invite import UseInviteRequest, use_invite_code

    mock_user = MagicMock()
    mock_user.user_id = str(uuid.uuid4())
    mock_db = AsyncMock()
    mock_request = MagicMock()
    mock_request.headers = {}
    mock_request.client = None

    with pytest.raises(HTTPException) as exc_info:
        await use_invite_code(
            body=UseInviteRequest(code="X" * 17),
            request=mock_request,
            current_user=mock_user,
            db=mock_db,
        )
    assert exc_info.value.status_code == 400
