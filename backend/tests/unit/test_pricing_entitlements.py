"""Unit tests for billing/pricing.py and membership/__init__.py.

Pricing model (2026-08 overhaul): access is universal — every tier can use
deepseek+grok, mimo+fish TTS/clone. Tiers differ only in which items are
*complimentary* (charged 0), driven by each tier's ``free`` list:
  - free:      nothing free (pay-per-use for everything)
  - plus:      deepseek, tts, asr, story_unlock
  - immersive: deepseek, grok, tts, clone, asr, story_unlock, story_chat
Claude is fully removed from all tiers.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock


# ---------------------------------------------------------------------------
# billing/pricing.py — llm_cost_fen (tier-aware)
# ---------------------------------------------------------------------------

class TestLlmCostFen:
    def test_deepseek_costs_100_fen_on_free(self):
        from heart.billing.pricing import llm_cost_fen
        # deepseek_cost_credits=1 → 100 fen; free tier has empty free list.
        assert llm_cost_fen("deepseek") == 100
        assert llm_cost_fen("deepseek-chat") == 100
        assert llm_cost_fen("deepseek-reasoner") == 100

    def test_deepseek_free_on_plus(self):
        from heart.billing.pricing import llm_cost_fen
        assert llm_cost_fen("deepseek", "plus") == 0

    def test_deepseek_free_on_immersive(self):
        from heart.billing.pricing import llm_cost_fen
        assert llm_cost_fen("deepseek", "immersive") == 0

    def test_grok_costs_300_fen_on_free(self):
        from heart.billing.pricing import llm_cost_fen
        assert llm_cost_fen("grok") == 300

    def test_grok_still_charged_on_plus(self):
        from heart.billing.pricing import llm_cost_fen
        # plus free list has no "grok" → private chat still billed.
        assert llm_cost_fen("grok", "plus") == 300

    def test_grok_free_on_immersive(self):
        from heart.billing.pricing import llm_cost_fen
        assert llm_cost_fen("grok", "immersive") == 0

    def test_unknown_model_returns_zero(self):
        from heart.billing.pricing import llm_cost_fen
        assert llm_cost_fen("unknown-future-model") == 0
        assert llm_cost_fen("unknown-future-model", "immersive") == 0


class TestTtsCostFen:
    def test_mimo_costs_500_fen_on_free(self):
        from heart.billing.pricing import tts_cost_fen
        assert tts_cost_fen("mimo") == 500

    def test_fish_costs_800_fen_on_free(self):
        from heart.billing.pricing import tts_cost_fen
        assert tts_cost_fen("fish") == 800

    def test_tts_free_on_plus(self):
        from heart.billing.pricing import tts_cost_fen
        assert tts_cost_fen("mimo", "plus") == 0
        assert tts_cost_fen("fish", "plus") == 0

    def test_tts_free_on_immersive(self):
        from heart.billing.pricing import tts_cost_fen
        assert tts_cost_fen("fish", "immersive") == 0

    def test_minimax_is_zero(self):
        from heart.billing.pricing import tts_cost_fen
        assert tts_cost_fen("minimax") == 0

    def test_unknown_provider_returns_zero(self):
        from heart.billing.pricing import tts_cost_fen
        assert tts_cost_fen("unknown") == 0


class TestActionCostFen:
    def test_clone_mimo_costs_5000_fen_on_free(self):
        from heart.billing.pricing import action_cost_fen
        assert action_cost_fen("clone_mimo") == 5000

    def test_clone_fish_costs_10000_fen_on_free(self):
        from heart.billing.pricing import action_cost_fen
        assert action_cost_fen("clone_fish") == 10000

    def test_clone_still_charged_on_plus(self):
        from heart.billing.pricing import action_cost_fen
        # plus free list has no "clone" → clone still billed.
        assert action_cost_fen("clone_mimo", "plus") == 5000

    def test_clone_free_on_immersive(self):
        from heart.billing.pricing import action_cost_fen
        assert action_cost_fen("clone_mimo", "immersive") == 0
        assert action_cost_fen("clone_fish", "immersive") == 0

    def test_unknown_action_returns_zero(self):
        from heart.billing.pricing import action_cost_fen
        assert action_cost_fen("unknown_action") == 0


class TestStoryPricing:
    """Story mode (SS09) unlock + per-minute pricing. 1 coin = 100 fen."""

    def test_unlock_costs_4000_fen_on_free(self):
        from heart.billing.pricing import story_unlock_cost_fen
        # story_unlock_cost_coins=40 → 4000 fen.
        assert story_unlock_cost_fen() == 4000

    def test_unlock_free_on_plus(self):
        from heart.billing.pricing import story_unlock_cost_fen
        assert story_unlock_cost_fen("plus") == 0

    def test_unlock_free_on_immersive(self):
        from heart.billing.pricing import story_unlock_cost_fen
        assert story_unlock_cost_fen("immersive") == 0

    def test_minute_costs_100_fen_on_free(self):
        from heart.billing.pricing import story_minute_cost_fen
        # story_minute_cost_coins=1 → 100 fen.
        assert story_minute_cost_fen() == 100

    def test_minute_still_charged_on_plus(self):
        from heart.billing.pricing import story_minute_cost_fen
        # plus free list has no "story_chat" → per-minute still billed.
        assert story_minute_cost_fen("plus") == 100

    def test_minute_free_on_immersive(self):
        from heart.billing.pricing import story_minute_cost_fen
        assert story_minute_cost_fen("immersive") == 0


class TestVoiceCallPricing:
    """Voice-call per-minute pricing + tier free-minute allowance."""

    def test_minute_cost_is_2000_fen(self):
        from heart.billing.pricing import voice_call_minute_cost_fen
        # voice_call_minute_cost_coins=20 → 2000 fen (1min = 20币).
        assert voice_call_minute_cost_fen() == 2000

    def test_free_tier_has_no_free_minutes(self):
        from heart.membership import voice_call_free_minutes
        assert voice_call_free_minutes("free") == 0

    def test_plus_tier_has_10_free_minutes(self):
        from heart.membership import voice_call_free_minutes
        assert voice_call_free_minutes("plus") == 10

    def test_immersive_tier_has_60_free_minutes(self):
        from heart.membership import voice_call_free_minutes
        assert voice_call_free_minutes("immersive") == 60

    def test_unknown_tier_has_no_free_minutes(self):
        from heart.membership import voice_call_free_minutes
        assert voice_call_free_minutes("enterprise_unknown") == 0


class TestStoryTierGating:
    """_tier_can_unlock: all tiers can unlock all scenarios (fee-based, not tier-gated)."""

    def test_free_user_can_unlock_free_tier(self):
        from heart.api.routes_story import _tier_can_unlock
        assert _tier_can_unlock("free", free_tier=True) is True

    def test_free_user_can_unlock_non_free(self):
        from heart.api.routes_story import _tier_can_unlock
        assert _tier_can_unlock("free", free_tier=False) is True

    def test_plus_user_can_unlock_non_free(self):
        from heart.api.routes_story import _tier_can_unlock
        assert _tier_can_unlock("plus", free_tier=False) is True

    def test_immersive_user_can_unlock_non_free(self):
        from heart.api.routes_story import _tier_can_unlock
        assert _tier_can_unlock("immersive", free_tier=False) is True


# ---------------------------------------------------------------------------
# membership/__init__.py — entitlements (universal access; free lists differ)
# ---------------------------------------------------------------------------

class TestGetEntitlements:
    def test_all_tiers_include_deepseek_and_grok(self):
        from heart.membership import get_entitlements
        for tier in ("free", "plus", "immersive"):
            ent = get_entitlements(tier)
            assert "deepseek" in ent.models
            assert "grok" in ent.models
            assert "claude" not in ent.models  # claude fully removed

    def test_all_tiers_include_both_tts(self):
        from heart.membership import get_entitlements
        for tier in ("free", "plus", "immersive"):
            ent = get_entitlements(tier)
            assert set(ent.tts) == {"mimo", "fish"}

    def test_all_tiers_include_clone(self):
        from heart.membership import get_entitlements
        for tier in ("free", "plus", "immersive"):
            ent = get_entitlements(tier)
            # MiMo clone retired (zero-shot quality too poor) — Fish only now.
            assert set(ent.clone) == {"fish"}

    def test_free_tier_grants_nothing_free(self):
        from heart.membership import get_entitlements
        ent = get_entitlements("free")
        assert ent.free == []
        assert ent.monthly_grant_fen == 0

    def test_plus_tier_free_list(self):
        from heart.membership import get_entitlements
        ent = get_entitlements("plus")
        assert set(ent.free) == {"deepseek", "tts", "asr", "story_unlock"}

    def test_plus_tier_monthly_grant_300_coins(self):
        from heart.membership import get_entitlements
        ent = get_entitlements("plus")
        assert ent.monthly_grant_fen == 30000  # 300 coins × 100

    def test_immersive_tier_free_list(self):
        from heart.membership import get_entitlements
        ent = get_entitlements("immersive")
        assert set(ent.free) == {
            "deepseek", "grok", "tts", "clone", "asr", "story_unlock", "story_chat"
        }

    def test_immersive_tier_monthly_grant_700_coins(self):
        from heart.membership import get_entitlements
        ent = get_entitlements("immersive")
        assert ent.monthly_grant_fen == 70000  # 700 coins × 100

    def test_immersive_free_list_is_superset_of_plus(self):
        from heart.membership import get_entitlements
        plus = set(get_entitlements("plus").free)
        immersive = set(get_entitlements("immersive").free)
        assert plus.issubset(immersive)

    def test_unknown_tier_falls_back_to_free(self):
        from heart.membership import get_entitlements
        ent = get_entitlements("enterprise_unknown")
        free = get_entitlements("free")
        assert ent.free == free.free
        assert ent.models == free.models


class TestIsFreeForTier:
    def test_free_tier_pays_for_everything(self):
        from heart.membership import is_free_for_tier
        for item in ("deepseek", "grok", "tts", "clone", "asr",
                     "story_unlock", "story_chat"):
            assert is_free_for_tier("free", item) is False

    def test_plus_free_items(self):
        from heart.membership import is_free_for_tier
        assert is_free_for_tier("plus", "deepseek") is True
        assert is_free_for_tier("plus", "tts") is True
        assert is_free_for_tier("plus", "asr") is True
        assert is_free_for_tier("plus", "story_unlock") is True
        # not free on plus:
        assert is_free_for_tier("plus", "grok") is False
        assert is_free_for_tier("plus", "clone") is False
        assert is_free_for_tier("plus", "story_chat") is False

    def test_immersive_everything_free(self):
        from heart.membership import is_free_for_tier
        for item in ("deepseek", "grok", "tts", "clone", "asr",
                     "story_unlock", "story_chat"):
            assert is_free_for_tier("immersive", item) is True

    def test_unknown_tier_nothing_free(self):
        from heart.membership import is_free_for_tier
        assert is_free_for_tier("enterprise_unknown", "deepseek") is False


# ---------------------------------------------------------------------------
# membership/__init__.py — assertion helpers (access universal now)
# ---------------------------------------------------------------------------

class TestAssertModelAllowed:
    def test_deepseek_allowed_for_all_tiers(self):
        from heart.membership import assert_model_allowed
        for tier in ("free", "plus", "immersive"):
            assert_model_allowed(tier, "deepseek")  # must not raise

    def test_grok_allowed_for_all_tiers(self):
        from heart.membership import assert_model_allowed
        for tier in ("free", "plus", "immersive"):
            assert_model_allowed(tier, "grok")  # must not raise

    def test_claude_forbidden_everywhere(self):
        from heart.membership import ModelForbiddenError, assert_model_allowed
        for tier in ("free", "plus", "immersive"):
            with pytest.raises(ModelForbiddenError):
                assert_model_allowed(tier, "claude")


class TestAssertTtsAllowed:
    def test_both_providers_allowed_for_all_tiers(self):
        from heart.membership import assert_tts_allowed
        for tier in ("free", "plus", "immersive"):
            assert_tts_allowed(tier, "mimo")
            assert_tts_allowed(tier, "fish")


class TestAssertCloneAllowed:
    def test_clone_allowed_for_all_tiers(self):
        from heart.membership import CloneForbiddenError, assert_clone_allowed

        for tier in ("free", "plus", "immersive"):
            assert_clone_allowed(tier, "fish")
            # MiMo clone retired — must now be rejected on every tier.
            with pytest.raises(CloneForbiddenError):
                assert_clone_allowed(tier, "mimo")


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
                'relation "user_memberships" does not exist', None, None
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
    async def test_returns_models_field_without_claude(self):
        from heart.api.routes_credits import pricing
        result = await pricing()
        assert "models" in result
        model_ids = {m["id"] for m in result["models"]}
        assert model_ids == {"deepseek", "grok"}  # claude removed

    @pytest.mark.asyncio
    async def test_deepseek_cost_is_one_coin(self):
        from heart.api.routes_credits import pricing
        result = await pricing()
        deepseek = next(m for m in result["models"] if m["id"] == "deepseek")
        assert deepseek["cost"] == 1  # deepseek_cost_credits default

    @pytest.mark.asyncio
    async def test_membership_tiers_present(self):
        from heart.api.routes_credits import pricing
        result = await pricing()
        assert "membership_tiers" in result
        tier_ids = {t["tier"] for t in result["membership_tiers"]}
        assert tier_ids == {"free", "plus", "immersive"}
        for t in result["membership_tiers"]:
            assert "sku" in t
            assert "benefits" in t
            assert "price" in t

    @pytest.mark.asyncio
    async def test_tier_prices_are_29_and_69(self):
        from heart.api.routes_credits import pricing
        result = await pricing()
        by_tier = {t["tier"]: t for t in result["membership_tiers"]}
        assert by_tier["plus"]["price"] == 29
        assert by_tier["immersive"]["price"] == 69

    @pytest.mark.asyncio
    async def test_tier_monthly_grants_reported(self):
        from heart.api.routes_credits import pricing
        result = await pricing()
        by_tier = {t["tier"]: t for t in result["membership_tiers"]}
        assert by_tier["free"]["monthly_grant"] == 0
        assert by_tier["plus"]["monthly_grant"] == 300
        assert by_tier["immersive"]["monthly_grant"] == 700

    @pytest.mark.asyncio
    async def test_shop_present(self):
        from heart.api.routes_credits import pricing
        result = await pricing()
        assert "shop" in result
        assert len(result["shop"]) == 4
        skus = {s["sku"] for s in result["shop"]}
        assert skus == {"pack_6", "pack_18", "pack_48", "pack_128"}

    @pytest.mark.asyncio
    async def test_actions_include_tts_and_clone(self):
        from heart.api.routes_credits import pricing
        result = await pricing()
        action_ids = {a["id"] for a in result["actions"]}
        assert "tts_mimo" in action_ids
        assert "tts_fish" in action_ids
        # MiMo clone retired — only Fish (真人克隆) is offered now.
        assert "clone_mimo" not in action_ids
        assert "clone_fish" in action_ids


# ---------------------------------------------------------------------------
# POST /api/credits/checkin — daily check-in (20 coins/day, idempotent)
# ---------------------------------------------------------------------------

class TestDailyCheckin:
    """Handler exercised directly with a mocked DB + patched grant() — no Postgres."""

    def _token(self):
        from heart.core.auth import TokenData
        return TokenData(
            user_id="550e8400-e29b-41d4-a716-446655440000",
            email="test@example.com",
        )

    @pytest.mark.asyncio
    async def test_first_checkin_grants(self, monkeypatch):
        from heart.api import routes_credits

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None  # no tx yet today
        db.execute = AsyncMock(return_value=result_mock)

        granted = AsyncMock(return_value=2000)  # new balance in fen
        monkeypatch.setattr(routes_credits, "grant", granted)

        res = await routes_credits.daily_checkin(current_user=self._token(), db=db)
        assert res["granted"] is True
        assert res["already"] is False
        assert res["coins"] == 20
        assert res["balance"] == 20.0  # 2000 fen / 100

        _, kwargs = granted.call_args
        assert kwargs["idempotency_key"].startswith("checkin:")
        assert kwargs["ref_type"] == "checkin"
        assert kwargs["type_str"] == "grant"

    @pytest.mark.asyncio
    async def test_grants_daily_checkin_coins_amount(self, monkeypatch):
        from heart.api import routes_credits
        from heart.core.config import settings

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result_mock)

        granted = AsyncMock(return_value=settings.daily_checkin_coins * 100)
        monkeypatch.setattr(routes_credits, "grant", granted)

        await routes_credits.daily_checkin(current_user=self._token(), db=db)
        # grant amount (positional arg 3) == coins * 100 fen
        args, _ = granted.call_args
        assert args[2] == settings.daily_checkin_coins * 100

    @pytest.mark.asyncio
    async def test_second_checkin_same_day_is_idempotent(self, monkeypatch):
        from heart.api import routes_credits

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = 1  # tx already exists today
        db.execute = AsyncMock(return_value=result_mock)

        # grant() still invoked but ON CONFLICT DO NOTHING → balance unchanged.
        granted = AsyncMock(return_value=2000)
        monkeypatch.setattr(routes_credits, "grant", granted)

        res = await routes_credits.daily_checkin(current_user=self._token(), db=db)
        assert res["granted"] is False
        assert res["already"] is True
        assert res["coins"] == 20
