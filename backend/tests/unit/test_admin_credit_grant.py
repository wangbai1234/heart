"""Regression tests for the admin credit grant response semantics."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from heart.billing import GrantResult, IdempotencyConflictError


@pytest.mark.asyncio
async def test_admin_credit_grant_reports_newly_applied_amount():
    from heart.api.routes_admin import GrantCreditsRequest, admin_grant_credits

    uid = uuid.uuid4()
    body = GrantCreditsRequest(
        email="user@example.com",
        amount=240,
        note="manual grant",
        idempotency_key="admin:user:240",
    )

    with (
        patch(
            "heart.api.routes_admin._resolve_user",
            new=AsyncMock(return_value={"id": uid, "email": body.email}),
        ),
        patch(
            "heart.api.routes_admin.grant_with_result",
            new=AsyncMock(return_value=GrantResult(balance=29_850, applied=True)),
        ),
    ):
        result = await admin_grant_credits(body=body, _=None, db=AsyncMock())

    assert result.ok is True
    assert result.credited == 240
    assert result.new_balance == 298.5
    assert result.already_applied is False
    assert result.idempotency_key == "admin:user:240"


@pytest.mark.asyncio
async def test_admin_credit_grant_reports_idempotent_replay_without_false_credit():
    from heart.api.routes_admin import GrantCreditsRequest, admin_grant_credits

    uid = uuid.uuid4()
    body = GrantCreditsRequest(
        email="user@example.com",
        amount=240,
        idempotency_key="admin:user:240",
    )

    with (
        patch(
            "heart.api.routes_admin._resolve_user",
            new=AsyncMock(return_value={"id": uid, "email": body.email}),
        ),
        patch(
            "heart.api.routes_admin.grant_with_result",
            new=AsyncMock(return_value=GrantResult(balance=29_850, applied=False)),
        ),
    ):
        result = await admin_grant_credits(body=body, _=None, db=AsyncMock())

    assert result.ok is True
    assert result.credited == 0
    assert result.already_applied is True


@pytest.mark.asyncio
async def test_admin_credit_grant_rejects_key_owned_by_different_transaction():
    from heart.api.routes_admin import GrantCreditsRequest, admin_grant_credits

    uid = uuid.uuid4()
    body = GrantCreditsRequest(
        email="user@example.com",
        amount=240,
        idempotency_key="key-owned-by-another-user",
    )

    with (
        patch(
            "heart.api.routes_admin._resolve_user",
            new=AsyncMock(return_value={"id": uid, "email": body.email}),
        ),
        patch(
            "heart.api.routes_admin.grant_with_result",
            new=AsyncMock(side_effect=IdempotencyConflictError()),
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        await admin_grant_credits(body=body, _=None, db=AsyncMock())

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "idempotency_conflict"
