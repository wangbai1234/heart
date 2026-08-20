"""Billing pricing — model/TTS/action cost lookup.

All public functions return fen (1 display coin = 100 fen).
Values are config-driven: change settings.* env vars to reprice without redeploy.

Costs are *tier-aware*: each function takes a ``tier`` and returns 0 when the
item is complimentary on that tier (see membership_tiers_config's ``free`` list).
Access is universal — tiers differ only in which items are free vs charged.
"""

from __future__ import annotations

from heart.core.config import settings
from heart.infra.model_catalog import get_model_spec
from heart.membership import is_free_for_tier


def _fen(coins: float) -> int:
    """Convert display coins to integer fen (1 coin = 100 fen).

    Cost config fields are float (so fractional prices like 0.5 coin work), but
    all downstream billing — ``deduct_credits`` and the ``credits_balance``
    column — is integer fen. ``round`` keeps 0.5→50, 0.1→10 exact despite
    binary-float noise (0.1*100 == 10.000000000000002)."""
    return round(coins * 100)


def llm_cost_fen(model: str, tier: str = "free") -> int:
    """Return LLM cost in fen for one turn of the given model slug on *tier*.

    The authoritative product catalog owns prices, including fractional coins.
    Immersive membership waives every selectable text-model cost.
    """
    # Legacy aliases keep their historical pricing for migration callers;
    # new product slugs always use MODEL_CATALOG prices.
    if model in {"deepseek", "deepseek-chat", "deepseek-reasoner"}:
        if tier == "immersive":
            return 0
        return _fen(settings.deepseek_cost_credits)
    if model == "grok":
        return 0 if is_free_for_tier(tier, "grok") else _fen(settings.grok_cost_credits)
    spec = get_model_spec(model)
    if spec is None or is_free_for_tier(tier, "all_llm"):
        return 0
    return _fen(spec.cost_coins)


def tts_cost_fen(provider: str, tier: str = "free") -> int:
    """Return TTS cost in fen per synthesized voice bubble for *provider* on *tier*.

    TTS is complimentary on tiers whose free list contains "tts" (plus/immersive).
    MiniMax is legacy-free (bundled into voice turn cost pre-B4 era).
    """
    if is_free_for_tier(tier, "tts"):
        return 0
    _map = {
        "mimo": _fen(settings.mimo_tts_cost_credits),
        "fish": _fen(settings.fish_tts_cost_credits),
        "minimax": 0,
    }
    return _map.get(provider, 0)


def story_unlock_cost_fen(tier: str = "free") -> int:
    """Fen to permanently unlock one story scenario (charged once per scenario).

    Free on tiers whose free list contains "story_unlock" (plus/immersive).
    """
    if is_free_for_tier(tier, "story_unlock"):
        return 0
    return _fen(settings.story_unlock_cost_coins)


def story_minute_cost_fen(tier: str = "free") -> int:
    """Fen per full minute of story playtime (PR C2 heartbeat billing).

    Free on tiers whose free list contains "story_chat" (immersive).
    """
    if is_free_for_tier(tier, "story_chat"):
        return 0
    return _fen(settings.story_minute_cost_coins)


def voice_call_minute_cost_fen() -> int:
    """Fen per full minute of voice call beyond the monthly free allowance.

    Unlike other pricing helpers this is not tier-gated at the fen level —
    the tier only decides how many free minutes precede paid billing (see
    ``heart.membership.voice_call_free_minutes``). Once free minutes are spent,
    every tier pays the same per-minute rate.
    """
    return _fen(settings.voice_call_minute_cost_coins)


def action_cost_fen(action: str, tier: str = "free") -> int:
    """Return cost in fen for a one-shot action (voice clone etc.) on *tier*.

    Clone actions are complimentary on tiers whose free list contains "clone" (immersive).
    """
    if action.startswith("clone") and is_free_for_tier(tier, "clone"):
        return 0
    _map = {
        "clone_mimo": _fen(settings.clone_mimo_cost_credits),
        "clone_fish": _fen(settings.clone_fish_cost_credits),
    }
    return _map.get(action, 0)
