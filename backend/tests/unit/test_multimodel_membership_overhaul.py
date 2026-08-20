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
    assert all(not hasattr(model, "api_model") for model in MODEL_CATALOG)
    assert all(not hasattr(model, "credential_group") for model in MODEL_CATALOG)


def test_every_non_default_model_ends_with_gemini_failover() -> None:
    from heart.infra.model_catalog import DEFAULT_CHAT_MODEL, MODEL_CATALOG

    for model in MODEL_CATALOG:
        if model.id != DEFAULT_CHAT_MODEL:
            assert model.failover[-1] == DEFAULT_CHAT_MODEL


def test_gemini_and_claude_use_product_display_names() -> None:
    from heart.infra.model_catalog import MODEL_BY_ID

    assert MODEL_BY_ID["gemini-3.1"].label == "双子座 3.1"
    assert MODEL_BY_ID["gemini-3.1"].family == "双子座"
    for model_id in (
        "claude-haiku-4.5",
        "claude-sonnet-4.6",
        "claude-opus-4.6",
        "claude-opus-5",
    ):
        assert MODEL_BY_ID[model_id].label.startswith("小克 ")
        assert MODEL_BY_ID[model_id].family == "小克"


def test_selectable_models_use_provider_env_and_explicit_upstream_ids() -> None:
    """Product slugs must route through reusable provider configs, not hardcoded IDs."""
    from heart.infra.llm_providers.registry import initialize_registry
    from heart.infra.model_catalog import MODEL_CATALOG

    env = {
        "DEEPSEEK_API_KEY": "deepseek-test-key",
        "DEEPSEEK_BASE_URL": "https://deepseek.test",
        "MAIN_LLM_MODEL": "internal-main-model",
        "CHEAP_LLM_MODEL": "internal-cheap-model",
        "DEEPSEEK_V4_FLASH_MODEL": "chat-deepseek-flash",
        "DEEPSEEK_V4_PRO_MODEL": "chat-deepseek-pro",
        "GROK_API_KEY": "grok-test-key",
        "GROK_BASE_URL": "https://grok.test",
        "GROK_MODEL": "chat-grok-45",
        "GROK_46_MODEL": "chat-grok-46",
        "CLAUDE_API_KEY": "claude-test-key",
        "CLAUDE_BASE_URL": "https://claude.test",
        "CLAUDE_MODEL": "chat-claude-sonnet",
        "CLAUDE_HAIKU_MODEL": "chat-claude-haiku",
        "CLAUDE_OPUS_46_MODEL": "chat-claude-opus-46",
        "CLAUDE_OPUS_5_MODEL": "chat-claude-opus-5",
        "CLAUDE_API_STYLE": "anthropic",
        "GEMINI_API_KEY": "gemini-test-key",
        "GEMINI_BASE_URL": "https://gemini.test",
        "GEMINI_MODEL": "chat-gemini-31",
        "GPT_API_KEY": "gpt-test-key",
        "GPT_BASE_URL": "https://gpt.test",
        "GPT_MODEL": "chat-gpt-55",
        "GPT_LUNA_MODEL": "chat-gpt-luna",
        "GPT_SOL_MODEL": "chat-gpt-sol",
    }

    with patch.dict("os.environ", env, clear=True):
        registry = initialize_registry()

    assert all(registry.has_model(model.id) for model in MODEL_CATALOG)
    assert registry.get_canonical_model("gemini-3.1") == "chat-gemini-31"
    assert registry.get_canonical_model("deepseek-v4-flash") == "chat-deepseek-flash"
    assert registry.get_canonical_model("deepseek-v4-pro") == "chat-deepseek-pro"
    assert registry.get_canonical_model("claude-haiku-4.5") == "chat-claude-haiku"
    assert registry.get_canonical_model("claude-sonnet-4.6") == "chat-claude-sonnet"
    assert registry.get_canonical_model("claude-opus-4.6") == "chat-claude-opus-46"
    assert registry.get_canonical_model("claude-opus-5") == "chat-claude-opus-5"
    assert registry.get_canonical_model("grok-4.5") == "chat-grok-45"
    assert registry.get_canonical_model("grok-4.6") == "chat-grok-46"
    assert registry.get_canonical_model("gpt-5.5") == "chat-gpt-55"
    assert registry.get_canonical_model("gpt-5.6-luna") == "chat-gpt-luna"
    assert registry.get_canonical_model("gpt-5.6-sol") == "chat-gpt-sol"

    # Existing provider instances are reused rather than shadowed by MICU_* groups.
    assert registry.get_provider_for_model("grok-4.5") is registry.get_provider("grok")
    assert registry.get_provider_for_model("claude-opus-5") is registry.get_provider("claude")
    assert registry.get_provider_for_model("deepseek-v4-flash") is registry.get_provider(
        "deepseek-v4-flash"
    )

    # Background routing remains on its original model settings in this PR.
    assert registry.get_canonical_model("internal-main-model") == "internal-main-model"
    assert registry.get_canonical_model("internal-cheap-model") == "internal-cheap-model"


@pytest.mark.parametrize(
    ("model", "coins"),
    [("gemini-3.1", 0.5), ("claude-sonnet-4.6", 2), ("claude-opus-5", 3)],
)
def test_new_model_prices_are_in_display_coins(model: str, coins: float) -> None:
    from heart.billing.pricing import llm_cost_fen

    assert llm_cost_fen(model, "free") == round(coins * 100)


def test_all_tiers_can_access_every_model_but_immersive_is_free() -> None:
    from heart.billing.pricing import llm_cost_fen
    from heart.infra.model_catalog import MODEL_CATALOG
    from heart.membership import assert_model_allowed, get_entitlements

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
