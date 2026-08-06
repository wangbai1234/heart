"""Billing pricing — model/TTS/action cost lookup.

All public functions return fen (1 display coin = 100 fen).
Values are config-driven: change settings.* env vars to reprice without redeploy.

Costs are *tier-aware*: each function takes a ``tier`` and returns 0 when the
item is complimentary on that tier (see membership_tiers_config's ``free`` list).
Access is universal — tiers differ only in which items are free vs charged.
"""

from __future__ import annotations

from heart.core.config import settings
from heart.membership import is_free_for_tier


def llm_cost_fen(model: str, tier: str = "free") -> int:
    """Return LLM cost in fen for one turn of the given model slug on *tier*.

    DeepSeek (普通交流) costs ``deepseek_cost_credits`` unless free on this tier.
    Grok (私密陪伴) costs ``grok_cost_credits`` unless free on this tier.
    Unknown models default to 0 (safe for future providers with no pricing yet).
    """
    _map = {
        "deepseek": ("deepseek", settings.deepseek_cost_credits * 100),
        "deepseek-chat": ("deepseek", settings.deepseek_cost_credits * 100),
        "deepseek-reasoner": ("deepseek", settings.deepseek_cost_credits * 100),
        "grok": ("grok", settings.grok_cost_credits * 100),
        "claude": ("claude", settings.claude_cost_credits * 100),
    }
    item, cost = _map.get(model, ("", 0))
    if not item or is_free_for_tier(tier, item):
        return 0
    return cost


def tts_cost_fen(provider: str, tier: str = "free") -> int:
    """Return TTS cost in fen per synthesized voice bubble for *provider* on *tier*.

    TTS is complimentary on tiers whose free list contains "tts" (plus/immersive).
    MiniMax is legacy-free (bundled into voice turn cost pre-B4 era).
    """
    if is_free_for_tier(tier, "tts"):
        return 0
    _map = {
        "mimo": settings.mimo_tts_cost_credits * 100,
        "fish": settings.fish_tts_cost_credits * 100,
        "minimax": 0,
    }
    return _map.get(provider, 0)


def story_unlock_cost_fen(tier: str = "free") -> int:
    """Fen to permanently unlock one story scenario (charged once per scenario).

    Free on tiers whose free list contains "story_unlock" (plus/immersive).
    """
    if is_free_for_tier(tier, "story_unlock"):
        return 0
    return settings.story_unlock_cost_coins * 100


def story_minute_cost_fen(tier: str = "free") -> int:
    """Fen per full minute of story playtime (PR C2 heartbeat billing).

    Free on tiers whose free list contains "story_chat" (immersive).
    """
    if is_free_for_tier(tier, "story_chat"):
        return 0
    return settings.story_minute_cost_coins * 100


def voice_call_minute_cost_fen() -> int:
    """Fen per full minute of voice call beyond the monthly free allowance.

    Unlike other pricing helpers this is not tier-gated at the fen level —
    the tier only decides how many free minutes precede paid billing (see
    ``heart.membership.voice_call_free_minutes``). Once free minutes are spent,
    every tier pays the same per-minute rate.
    """
    return settings.voice_call_minute_cost_coins * 100


def action_cost_fen(action: str, tier: str = "free") -> int:
    """Return cost in fen for a one-shot action (voice clone etc.) on *tier*.

    Clone actions are complimentary on tiers whose free list contains "clone" (immersive).
    """
    if action.startswith("clone") and is_free_for_tier(tier, "clone"):
        return 0
    _map = {
        "clone_mimo": settings.clone_mimo_cost_credits * 100,
        "clone_fish": settings.clone_fish_cost_credits * 100,
    }
    return _map.get(action, 0)
