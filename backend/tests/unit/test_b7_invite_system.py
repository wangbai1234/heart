"""B7 unit tests: invite codes, signup recording, first-chat rewards."""

from __future__ import annotations

import uuid
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
        _empty_mapping_result(),                       # first SELECT: nothing
        MagicMock(),                                   # INSERT
        _mapping_result({"code": "NEWCDE42"}),        # second SELECT
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
async def test_record_invite_signup_unknown_code_returns_false():
    from heart.invite.service import record_invite_signup

    db = _mock_db(_empty_mapping_result())
    result = await record_invite_signup(db, uuid.uuid4(), "NOTEXIST")

    assert result is False
    assert db.execute.await_count == 1  # only SELECT


@pytest.mark.asyncio
async def test_record_invite_signup_self_invite_returns_false():
    from heart.invite.service import record_invite_signup

    user_id = uuid.uuid4()
    db = _mock_db(_mapping_result({"user_id": user_id}))
    result = await record_invite_signup(db, user_id, "SELFCODE")

    assert result is False


@pytest.mark.asyncio
async def test_record_invite_signup_valid_returns_true():
    from heart.invite.service import record_invite_signup

    inviter_id = uuid.uuid4()
    db = _mock_db(
        _mapping_result({"user_id": inviter_id}),  # SELECT inviter
        MagicMock(),                                # INSERT
    )
    result = await record_invite_signup(db, uuid.uuid4(), "GOODCODE")

    assert result is True
    assert db.execute.await_count == 2


# ── handle_first_chat ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_handle_first_chat_no_invite_record_skips():
    from heart.invite.service import handle_first_chat

    db = _mock_db(_empty_mapping_result())

    with patch("heart.invite.service.grant_credits") as mock_grant:
        await handle_first_chat(db, uuid.uuid4())

    mock_grant.assert_not_called()


@pytest.mark.asyncio
async def test_handle_first_chat_already_claimed_skips():
    """UPDATE RETURNING nothing → raced, skip rewards."""
    from heart.invite.service import handle_first_chat

    inviter_id = uuid.uuid4()
    invitee_id = uuid.uuid4()
    use_id = 42

    db = _mock_db(
        _mapping_result({"id": use_id, "inviter_id": inviter_id}),  # SELECT pending
        _fetchone_result(None),                                       # UPDATE RETURNING → raced
    )

    with patch("heart.invite.service.grant_credits") as mock_grant:
        await handle_first_chat(db, invitee_id)

    mock_grant.assert_not_called()


@pytest.mark.asyncio
async def test_handle_first_chat_grants_both_parties():
    """Successful first chat: inviter and invitee both receive coins."""
    from heart.invite.service import handle_first_chat

    inviter_id = uuid.uuid4()
    invitee_id = uuid.uuid4()
    use_id = 7

    db = _mock_db(
        _mapping_result({"id": use_id, "inviter_id": inviter_id}),  # SELECT pending
        _fetchone_result((use_id,)),                                  # UPDATE RETURNING claimed
        _fetchone_result((1,)),                                       # COUNT (1 invite, no milestone)
    )

    with patch("heart.invite.service.grant_credits", new_callable=AsyncMock) as mock_grant, \
         patch("heart.invite.service.settings") as mock_settings:
        mock_settings.invite_referral_grant_coins = 100
        mock_settings.invite_milestone_5_coins = 300
        mock_settings.invite_milestone_10_coins = 1000
        await handle_first_chat(db, invitee_id)

    assert mock_grant.await_count == 2
    calls = mock_grant.call_args_list
    assert calls[0].args[1] == invitee_id
    assert calls[0].args[2] == 10000  # 100 coins × 100 fen
    assert "invitee" in calls[0].kwargs["idempotency_key"]
    assert calls[1].args[1] == inviter_id
    assert calls[1].args[2] == 10000
    assert "inviter" in calls[1].kwargs["idempotency_key"]


@pytest.mark.asyncio
async def test_handle_first_chat_grants_milestone_5():
    """After 5th invite, milestone bonus is granted."""
    from heart.invite.service import handle_first_chat

    inviter_id = uuid.uuid4()
    invitee_id = uuid.uuid4()
    use_id = 15

    db = _mock_db(
        _mapping_result({"id": use_id, "inviter_id": inviter_id}),
        _fetchone_result((use_id,)),   # UPDATE claimed
        _fetchone_result((5,)),        # COUNT = 5 → milestone_5
        _fetchone_result((use_id,)),   # UPDATE milestone_10 → none (cnt<10, but 5 >= 5 first)
        _fetchone_result((use_id,)),   # UPDATE milestone_5 → claimed
    )

    with patch("heart.invite.service.grant_credits", new_callable=AsyncMock) as mock_grant, \
         patch("heart.invite.service.settings") as mock_settings:
        mock_settings.invite_referral_grant_coins = 100
        mock_settings.invite_milestone_5_coins = 300
        mock_settings.invite_milestone_10_coins = 1000
        await handle_first_chat(db, invitee_id)

    # 2 base grants + 1 milestone grant
    assert mock_grant.await_count == 3
    milestone_call = mock_grant.call_args_list[2]
    assert milestone_call.args[2] == 30000  # 300 coins × 100 fen
    assert "milestone" in milestone_call.kwargs["idempotency_key"]


# ── GET /api/invite endpoint ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_invite_endpoint_returns_code_and_url():
    from heart.api.routes_invite import get_invite_info

    user_id = uuid.uuid4()
    mock_user = MagicMock()
    mock_user.user_id = str(user_id)
    mock_db = AsyncMock()

    with patch("heart.api.routes_invite.get_or_create_code", new_callable=AsyncMock, return_value="ABCD1234"):
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

    with patch("heart.api.routes_invite.record_invite_signup", new_callable=AsyncMock, return_value=True):
        result = await use_invite_code(
            body=UseInviteRequest(code="GOODCODE"),
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

    with pytest.raises(HTTPException) as exc_info:
        await use_invite_code(
            body=UseInviteRequest(code="X" * 17),
            current_user=mock_user,
            db=mock_db,
        )
    assert exc_info.value.status_code == 400
