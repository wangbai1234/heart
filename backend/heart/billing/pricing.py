"""Billing pricing — model/TTS/action cost lookup.

All public functions return fen (1 display coin = 100 fen).
Values are config-driven: change settings.* env vars to reprice without redeploy.
"""

from __future__ import annotations

from heart.core.config import settings


def llm_cost_fen(model: str) -> int:
    """Return LLM cost in fen for one turn of the given model slug.

    DeepSeek is free (0 fen) to reduce churn.
    Unknown models default to 0 (safe for future providers with no pricing yet).
    """
    _map = {
        "deepseek": 0,
        "deepseek-chat": 0,
        "deepseek-reasoner": 0,
        "grok": settings.grok_cost_credits * 100,
        "claude": settings.claude_cost_credits * 100,
    }
    return _map.get(model, 0)


def tts_cost_fen(provider: str) -> int:
    """Return TTS cost in fen per synthesized voice bubble for the given provider slug.

    MiniMax is legacy-free (bundled into voice turn cost pre-B4 era).
    """
    _map = {
        "mimo": settings.mimo_tts_cost_credits * 100,
        "fish": settings.fish_tts_cost_credits * 100,
        "minimax": 0,
    }
    return _map.get(provider, 0)


def story_unlock_cost_fen() -> int:
    """Fen to permanently unlock one story scenario (charged once per scenario)."""
    return settings.story_unlock_cost_coins * 100


def story_minute_cost_fen() -> int:
    """Fen per full minute of story playtime (PR C2 heartbeat billing)."""
    return settings.story_minute_cost_coins * 100


def action_cost_fen(action: str) -> int:
    """Return cost in fen for a one-shot action (voice clone etc.)."""
    _map = {
        "clone_mimo": settings.clone_mimo_cost_credits * 100,
        "clone_fish": settings.clone_fish_cost_credits * 100,
    }
    return _map.get(action, 0)
