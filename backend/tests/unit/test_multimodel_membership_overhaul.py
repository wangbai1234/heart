"""Focused coverage for the yuoyuo multi-model and permanent coin rules."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def test_catalog_has_all_selectable_models_and_default() -> None:
    from heart.infra.model_catalog import DEFAULT_CHAT_MODEL, MODEL_CATALOG

    assert DEFAULT_CHAT_MODEL == "gemini-3.1"
    assert len(MODEL_CATALOG) == 12
    assert {model.id for model in MODEL_CATALOG} == {
        "gemini-3.1",
        "deepseek-v4-flash",
        "deepseek-v4-pro",
        "claude-haiku-4.5",
        "claude-sonnet-4.6",
        "claude-opus-4.6",
        "claude-opus-5",
        "grok-4.5",
        "grok-4.6",
        "gpt-5.6-luna",
        "gpt-5.5",
        "gpt-5.6-sol",
    }


@pytest.mark.parametrize(
    ("model", "coins"),
    [("gemini-3.1", 0.5), ("claude-sonnet-4.6", 2), ("claude-opus-5", 3)],
)
def test_new_model_prices_are_in_display_coins(model: str, coins: float) -> None:
    from heart.billing.pricing import llm_cost_fen

    assert llm_cost_fen(model, "free") == round(coins * 100)


def test_all_tiers_can_access_every_model_but_immersive_is_free() -> None:
    from heart.infra.model_catalog import MODEL_CATALOG
    from heart.membership import assert_model_allowed, get_entitlements
    from heart.billing.pricing import llm_cost_fen

    for tier in ("free", "plus", "immersive"):
        entitlements = get_entitlements(tier)
        for model in MODEL_CATALOG:
            assert_model_allowed(tier, model.id)
            assert model.id in entitlements.models
    assert llm_cost_fen("gpt-5.6-sol", "plus") == 200
    assert llm_cost_fen("gpt-5.6-sol", "immersive") == 0


def test_daily_targets_are_free_20_and_paid_80() -> None:
    from heart.billing.checkin import daily_target_for_tier

    assert daily_target_for_tier("free") == 20
    assert daily_target_for_tier("plus") == 80
    assert daily_target_for_tier("immersive") == 80


@pytest.mark.asyncio
async def test_same_day_paid_upgrade_only_tops_up_remaining_coins() -> None:
    from heart.billing.checkin import claim_daily_grant

    db = AsyncMock()
    query_result = MagicMock()
    query_result.scalar_one.return_value = 2_000  # free check-in already claimed
    db.execute.return_value = query_result
    user_id = uuid.uuid4()

    with patch("heart.billing.checkin.grant", new=AsyncMock(return_value=9_999)) as grant_mock:
        result = await claim_daily_grant(db, user_id, "plus", day="2026-08-20")

    assert result["coins"] == 60
    assert result["daily_total"] == 80
    grant_mock.assert_awaited_once()
    assert grant_mock.call_args.args[2] == 6_000


@pytest.mark.asyncio
async def test_daily_grant_is_idempotent_when_target_already_reached() -> None:
    from heart.billing.checkin import claim_daily_grant

    db = AsyncMock()
    query_result = MagicMock()
    query_result.scalar_one.return_value = 8_000
    balance_result = MagicMock()
    balance_result.scalar_one_or_none.return_value = 8_000
    db.execute.side_effect = [query_result, balance_result]

    with patch("heart.billing.checkin.grant", new=AsyncMock()) as grant_mock:
        result = await claim_daily_grant(db, uuid.uuid4(), "plus", day="2026-08-20")

    assert result["already"] is True
    assert result["coins"] == 0
    grant_mock.assert_not_awaited()
