"""Unit tests for billing/pricing.py and membership/__init__.py (B1)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# billing/pricing.py
# ---------------------------------------------------------------------------

class TestLlmCostFen:
    def test_deepseek_is_free(self):
        from heart.billing.pricing import llm_cost_fen
        assert llm_cost_fen("deepseek") == 0

    def test_deepseek_chat_is_free(self):
        from heart.billing.pricing import llm_cost_fen
        assert llm_cost_fen("deepseek-chat") == 0

    def test_deepseek_reasoner_is_free(self):
        from heart.billing.pricing import llm_cost_fen
        assert llm_cost_fen("deepseek-reasoner") == 0

    def test_grok_costs_300_fen(self):
        from heart.billing.pricing import llm_cost_fen
        # Default config: grok_cost_credits=3 → 300 fen
        assert llm_cost_fen("grok") == 300

    def test_claude_costs_1200_fen(self):
        from heart.billing.pricing import llm_cost_fen
        # Default config: claude_cost_credits=12 → 1200 fen
        assert llm_cost_fen("claude") == 1200

    def test_unknown_model_returns_zero(self):
        from heart.billing.pricing import llm_cost_fen
        assert llm_cost_fen("unknown-future-model") == 0


class TestTtsCostFen:
    def test_mimo_costs_500_fen(self):
        from heart.billing.pricing import tts_cost_fen
        assert tts_cost_fen("mimo") == 500

    def test_fish_costs_800_fen(self):
        from heart.billing.pricing import tts_cost_fen
        assert tts_cost_fen("fish") == 800

    def test_minimax_is_zero(self):
        from heart.billing.pricing import tts_cost_fen
        assert tts_cost_fen("minimax") == 0

    def test_unknown_provider_returns_zero(self):
        from heart.billing.pricing import tts_cost_fen
        assert tts_cost_fen("unknown") == 0


class TestActionCostFen:
    def test_clone_mimo_costs_5000_fen(self):
        from heart.billing.pricing import action_cost_fen
        assert action_cost_fen("clone_mimo") == 5000

    def test_clone_fish_costs_10000_fen(self):
        from heart.billing.pricing import action_cost_fen
        assert action_cost_fen("clone_fish") == 10000

    def test_unknown_action_returns_zero(self):
        from heart.billing.pricing import action_cost_fen
        assert action_cost_fen("unknown_action") == 0


# ---------------------------------------------------------------------------
# membership/__init__.py — entitlements
# ---------------------------------------------------------------------------

class TestGetEntitlements:
    def test_free_tier_models(self):
        from heart.membership import get_entitlements
        ent = get_entitlements("free")
        assert "deepseek" in ent.models
        assert "grok" not in ent.models
        assert "claude" not in ent.models

    def test_free_tier_no_fish_tts(self):
        from heart.membership import get_entitlements
        ent = get_entitlements("free")
        assert "mimo" in ent.tts
        assert "fish" not in ent.tts

    def test_free_tier_no_clone(self):
        from heart.membership import get_entitlements
        ent = get_entitlements("free")
        assert ent.clone == []

    def test_free_tier_no_monthly_grant(self):
        from heart.membership import get_entitlements
        ent = get_entitlements("free")
        assert ent.monthly_grant_fen == 0

    def test_plus_tier_includes_grok(self):
        from heart.membership import get_entitlements
        ent = get_entitlements("plus")
        assert "grok" in ent.models
        assert "claude" not in ent.models

    def test_plus_tier_includes_fish(self):
        from heart.membership import get_entitlements
        ent = get_entitlements("plus")
        assert "fish" in ent.tts

    def test_plus_tier_monthly_grant_400_coins(self):
        from heart.membership import get_entitlements
        ent = get_entitlements("plus")
        assert ent.monthly_grant_fen == 40000  # 400 coins × 100

    def test_immersive_tier_includes_claude(self):
        from heart.membership import get_entitlements
        ent = get_entitlements("immersive")
        assert "claude" in ent.models
        assert "grok" in ent.models

    def test_immersive_tier_monthly_grant_800_coins(self):
        from heart.membership import get_entitlements
        ent = get_entitlements("immersive")
        assert ent.monthly_grant_fen == 80000  # 800 coins × 100

    def test_immersive_is_superset_of_plus(self):
        from heart.membership import get_entitlements
        plus = get_entitlements("plus")
        immersive = get_entitlements("immersive")
        assert set(plus.models).issubset(set(immersive.models))
        assert set(plus.tts).issubset(set(immersive.tts))
        assert set(plus.clone).issubset(set(immersive.clone))

    def test_unknown_tier_falls_back_to_free(self):
        from heart.membership import get_entitlements
        ent = get_entitlements("enterprise_unknown")
        free = get_entitlements("free")
        assert ent.models == free.models


# ---------------------------------------------------------------------------
# membership/__init__.py — assertion helpers
# ---------------------------------------------------------------------------

class TestAssertModelAllowed:
    def test_deepseek_allowed_for_free(self):
        from heart.membership import assert_model_allowed
        assert_model_allowed("free", "deepseek")  # must not raise

    def test_grok_forbidden_for_free(self):
        from heart.membership import ModelForbiddenError, assert_model_allowed
        with pytest.raises(ModelForbiddenError) as exc_info:
            assert_model_allowed("free", "grok")
        assert exc_info.value.model == "grok"
        assert exc_info.value.tier == "free"

    def test_claude_forbidden_for_free(self):
        from heart.membership import ModelForbiddenError, assert_model_allowed
        with pytest.raises(ModelForbiddenError):
            assert_model_allowed("free", "claude")

    def test_grok_allowed_for_plus(self):
        from heart.membership import assert_model_allowed
        assert_model_allowed("plus", "grok")  # must not raise

    def test_claude_forbidden_for_plus(self):
        from heart.membership import ModelForbiddenError, assert_model_allowed
        with pytest.raises(ModelForbiddenError):
            assert_model_allowed("plus", "claude")

    def test_claude_allowed_for_immersive(self):
        from heart.membership import assert_model_allowed
        assert_model_allowed("immersive", "claude")  # must not raise


class TestAssertTtsAllowed:
    def test_mimo_allowed_for_free(self):
        from heart.membership import assert_tts_allowed
        assert_tts_allowed("free", "mimo")

    def test_fish_forbidden_for_free(self):
        from heart.membership import TtsForbiddenError, assert_tts_allowed
        with pytest.raises(TtsForbiddenError) as exc_info:
            assert_tts_allowed("free", "fish")
        assert exc_info.value.provider == "fish"

    def test_fish_allowed_for_plus(self):
        from heart.membership import assert_tts_allowed
        assert_tts_allowed("plus", "fish")

    def test_fish_allowed_for_immersive(self):
        from heart.membership import assert_tts_allowed
        assert_tts_allowed("immersive", "fish")


class TestAssertCloneAllowed:
    def test_clone_forbidden_entirely_for_free(self):
        from heart.membership import CloneForbiddenError, assert_clone_allowed
        with pytest.raises(CloneForbiddenError):
            assert_clone_allowed("free", "mimo")
        with pytest.raises(CloneForbiddenError):
            assert_clone_allowed("free", "fish")

    def test_mimo_clone_allowed_for_plus(self):
        from heart.membership import assert_clone_allowed
        assert_clone_allowed("plus", "mimo")

    def test_fish_clone_allowed_for_plus(self):
        from heart.membership import assert_clone_allowed
        assert_clone_allowed("plus", "fish")

    def test_fish_clone_allowed_for_immersive(self):
        from heart.membership import assert_clone_allowed
        assert_clone_allowed("immersive", "fish")


# ---------------------------------------------------------------------------
# membership/__init__.py — get_effective_tier (async, with mock DB)
# ---------------------------------------------------------------------------

class TestGetEffectiveTier:
    @pytest.mark.asyncio
    async def test_returns_free_when_no_row(self):
        import uuid
        from heart.membership import get_effective_tier

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result_mock)

        tier = await get_effective_tier(db, uuid.uuid4())
        assert tier == "free"

    @pytest.mark.asyncio
    async def test_returns_active_tier(self):
        import uuid
        from heart.membership import get_effective_tier

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = "plus"
        db.execute = AsyncMock(return_value=result_mock)

        tier = await get_effective_tier(db, uuid.uuid4())
        assert tier == "plus"

    @pytest.mark.asyncio
    async def test_returns_free_when_table_missing(self):
        import uuid
        from sqlalchemy.exc import ProgrammingError
        from heart.membership import get_effective_tier

        db = AsyncMock()
        db.execute = AsyncMock(
            side_effect=ProgrammingError(
                "relation \"user_memberships\" does not exist", None, None
            )
        )
        db.rollback = AsyncMock()

        tier = await get_effective_tier(db, uuid.uuid4())
        assert tier == "free"
        db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_propagates_unrelated_db_errors(self):
        import uuid
        from sqlalchemy.exc import OperationalError
        from heart.membership import get_effective_tier

        db = AsyncMock()
        db.execute = AsyncMock(
            side_effect=OperationalError("connection refused", None, None)
        )

        with pytest.raises(OperationalError):
            await get_effective_tier(db, uuid.uuid4())


# ---------------------------------------------------------------------------
# GET /api/credits/pricing — extended response
# ---------------------------------------------------------------------------

class TestPricingEndpoint:
    @pytest.mark.asyncio
    async def test_returns_models_field(self):
        from heart.api.routes_credits import pricing
        result = await pricing()
        assert "models" in result
        model_ids = {m["id"] for m in result["models"]}
        assert "deepseek" in model_ids
        assert "grok" in model_ids
        assert "claude" in model_ids

    @pytest.mark.asyncio
    async def test_deepseek_cost_is_zero(self):
        from heart.api.routes_credits import pricing
        result = await pricing()
        deepseek = next(m for m in result["models"] if m["id"] == "deepseek")
        assert deepseek["cost"] == 0

    @pytest.mark.asyncio
    async def test_membership_tiers_present(self):
        from heart.api.routes_credits import pricing
        result = await pricing()
        assert "membership_tiers" in result
        # field renamed: id → tier (api_contract.md §1.1)
        tier_ids = {t["tier"] for t in result["membership_tiers"]}
        assert tier_ids == {"free", "plus", "immersive"}
        # each tier has sku and benefits
        for t in result["membership_tiers"]:
            assert "sku" in t
            assert "benefits" in t
            assert "price" in t  # renamed from price_monthly

    @pytest.mark.asyncio
    async def test_shop_present(self):
        from heart.api.routes_credits import pricing
        result = await pricing()
        assert "shop" in result
        assert len(result["shop"]) == 4
        # SKU names aligned to contract
        skus = {s["sku"] for s in result["shop"]}
        assert skus == {"pack_6", "pack_18", "pack_48", "pack_128"}

    @pytest.mark.asyncio
    async def test_actions_include_tts(self):
        from heart.api.routes_credits import pricing
        result = await pricing()
        action_ids = {a["id"] for a in result["actions"]}
        assert "tts_mimo" in action_ids
        assert "tts_fish" in action_ids
        assert "clone_mimo" in action_ids
        assert "clone_fish" in action_ids
