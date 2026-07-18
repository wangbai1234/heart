"""Membership tier entitlements and enforcement.

Tier hierarchy: free < plus < immersive (immersive is a strict superset of plus).
Entitlements are fully config-driven via settings.membership_tiers_config (JSON).

Usage:
    tier = await get_effective_tier(db, user_id)  # lazy, no cache
    ent  = get_entitlements(tier)
    assert_model_allowed(tier, "grok")   # raises ModelForbiddenError if not allowed
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

import structlog
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from heart.core.config import settings

logger = structlog.get_logger(__name__)

VALID_TIERS = frozenset({"free", "plus", "immersive"})


@dataclass
class Entitlements:
    models: list[str]
    tts: list[str]
    clone: list[str]
    monthly_grant_fen: int


# ---------------------------------------------------------------------------
# Tier entitlements (config-driven)
# ---------------------------------------------------------------------------


def _parse_tiers() -> dict[str, Entitlements]:
    """Parse membership_tiers_config JSON → Entitlements map (called on each access)."""
    try:
        raw: dict = json.loads(settings.membership_tiers_config)
    except Exception:
        logger.exception("membership_tiers_config_parse_failed")
        raise
    result: dict[str, Entitlements] = {}
    for tier_name, v in raw.items():
        result[tier_name] = Entitlements(
            models=list(v.get("models", [])),
            tts=list(v.get("tts", [])),
            clone=list(v.get("clone", [])),
            monthly_grant_fen=int(v.get("monthly_grant", 0)) * 100,
        )
    return result


def get_entitlements(tier: str) -> Entitlements:
    """Return Entitlements for *tier*. Unknown tiers fall back to free."""
    tiers = _parse_tiers()
    return tiers.get(tier) or tiers["free"]


# ---------------------------------------------------------------------------
# Effective tier (lazily resolved from DB — no in-process cache)
# ---------------------------------------------------------------------------


async def get_effective_tier(db: AsyncSession, user_id: uuid.UUID) -> str:
    """Return user's current tier slug, falling back to 'free' when:
    - No active membership row exists
    - The membership has expired (expires_at <= NOW())
    - The user_memberships table does not yet exist (pre-migration-034 env)
    """
    try:
        result = await db.execute(
            text("""
                SELECT tier FROM user_memberships
                WHERE user_id = :uid
                  AND status = 'active'
                  AND expires_at > NOW()
                ORDER BY expires_at DESC
                LIMIT 1
            """),
            {"uid": user_id},
        )
        row = result.scalar_one_or_none()
        return row if row in VALID_TIERS else "free"
    except ProgrammingError as exc:
        # Table doesn't exist yet (migration 034 not yet applied).
        # This is expected during B1–B3 before B2 is merged.
        if "user_memberships" in str(exc):
            await db.rollback()
            logger.debug("membership_table_missing_fallback_free", user_id=str(user_id))
            return "free"
        logger.exception("get_effective_tier_db_error", user_id=str(user_id))
        raise


# ---------------------------------------------------------------------------
# Assertion helpers (raise structured exceptions for the API layer to translate)
# ---------------------------------------------------------------------------


class ModelForbiddenError(Exception):
    def __init__(self, model: str, tier: str) -> None:
        self.model = model
        self.tier = tier
        super().__init__(f"Model '{model}' not allowed on tier '{tier}'")


class TtsForbiddenError(Exception):
    def __init__(self, provider: str, tier: str) -> None:
        self.provider = provider
        self.tier = tier
        super().__init__(f"TTS provider '{provider}' not allowed on tier '{tier}'")


class CloneForbiddenError(Exception):
    def __init__(self, provider: str, tier: str) -> None:
        self.provider = provider
        self.tier = tier
        super().__init__(f"Clone provider '{provider}' not allowed on tier '{tier}'")


def assert_model_allowed(tier: str, model: str) -> None:
    """Raise ModelForbiddenError if *model* is not available on *tier*."""
    ent = get_entitlements(tier)
    if model not in ent.models:
        raise ModelForbiddenError(model=model, tier=tier)


def assert_tts_allowed(tier: str, provider: str) -> None:
    """Raise TtsForbiddenError if TTS *provider* is not available on *tier*."""
    ent = get_entitlements(tier)
    if provider not in ent.tts:
        raise TtsForbiddenError(provider=provider, tier=tier)


def assert_clone_allowed(tier: str, provider: str) -> None:
    """Raise CloneForbiddenError if clone *provider* is not available on *tier*."""
    ent = get_entitlements(tier)
    if provider not in ent.clone:
        raise CloneForbiddenError(provider=provider, tier=tier)
