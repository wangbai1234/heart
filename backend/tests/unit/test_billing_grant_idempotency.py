"""Unit coverage for credit-grant idempotency ownership checks."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from heart.billing import IdempotencyConflictError, grant_with_result


def _scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _mapping_result(value):
    result = MagicMock()
    result.mappings.return_value.one_or_none.return_value = value
    return result


@pytest.mark.asyncio
async def test_grant_replay_reports_not_applied_for_same_transaction():
    user_id = uuid.uuid4()
    db = AsyncMock()
    db.execute.side_effect = [
        _scalar_result(None),
        _mapping_result({"user_id": user_id, "delta": 24_000, "type": "grant"}),
        _scalar_result(29_850),
    ]

    result = await grant_with_result(
        db,
        user_id,
        24_000,
        idempotency_key="same-grant",
    )

    assert result.balance == 29_850
    assert result.applied is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("existing_user", "existing_delta", "existing_type"),
    [
        (uuid.uuid4(), 24_000, "grant"),
        (None, 10_000, "grant"),
        (None, 24_000, "refund"),
    ],
)
async def test_grant_rejects_key_owned_by_different_transaction(
    existing_user,
    existing_delta,
    existing_type,
):
    requested_user = uuid.uuid4()
    existing_user = existing_user or requested_user
    db = AsyncMock()
    db.execute.side_effect = [
        _scalar_result(None),
        _mapping_result(
            {
                "user_id": existing_user,
                "delta": existing_delta,
                "type": existing_type,
            }
        ),
    ]

    with pytest.raises(IdempotencyConflictError):
        await grant_with_result(
            db,
            requested_user,
            24_000,
            idempotency_key="conflicting-grant",
        )
