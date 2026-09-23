"""Production chat access gate backed by fulfilled Afdian orders."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _session_mock(*results):
    db = AsyncMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)
    db.execute = AsyncMock(side_effect=list(results))
    return db


@pytest.mark.asyncio
async def test_production_unpaid_user_gets_network_fluctuation_error():
    from heart.api.routes_chat_ws import _precheck_billing
    from heart.core.config import settings

    paid_result = MagicMock()
    paid_result.scalar.return_value = False
    db = _session_mock(paid_result)
    ws = AsyncMock()
    user_id = uuid.uuid4()

    with (
        patch.object(settings, "environment", "production"),
        patch.object(settings, "heart_env", "prod"),
        patch("heart.api.routes_chat_ws._get_engine"),
        patch("sqlalchemy.ext.asyncio.AsyncSession", return_value=db),
    ):
        effective_voice, can_proceed = await _precheck_billing(user_id, "rin", "turn-1", ws)

    assert effective_voice is False
    assert can_proceed is False
    assert ws.send_json.await_args.args[0] == {
        "type": "error",
        "code": "NETWORK_FLUCTUATION",
        "turn_id": "turn-1",
        "character_id": "rin",
        "msg": "网络波动异常，请稍后再试",
    }


@pytest.mark.asyncio
async def test_production_paid_user_passes_to_normal_billing_checks():
    from heart.api.routes_chat_ws import _precheck_billing
    from heart.core.config import settings

    paid_result = MagicMock()
    paid_result.scalar.return_value = True
    voice_result = MagicMock()
    voice_result.scalar_one_or_none.return_value = False
    balance_result = MagicMock()
    balance_result.scalar_one_or_none.return_value = 100000
    db = _session_mock(paid_result, voice_result, balance_result)
    ws = AsyncMock()

    with (
        patch.object(settings, "environment", "production"),
        patch.object(settings, "heart_env", "prod"),
        patch("heart.api.routes_chat_ws._get_engine"),
        patch("sqlalchemy.ext.asyncio.AsyncSession", return_value=db),
        patch("heart.membership.get_effective_tier", new=AsyncMock(return_value="free")),
    ):
        effective_voice, can_proceed = await _precheck_billing(uuid.uuid4(), "rin", "turn-2", ws)

    assert effective_voice is False
    assert can_proceed is True
    assert ws.send_json.await_count == 0
