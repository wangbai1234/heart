"""DB-driven voice resolver — replaces hardcoded VOICE_CATALOG for UGC characters.

Priority:
  1. character_voices row (DB, covers both preset and clone)
  2. voice_catalog.py legacy lookup (built-in rin/dorothy fallback)

Since migration 039 a character may have MULTIPLE voice rows — one per provider
(mimo / fish / minimax). ``resolve_effective_voice`` is the authoritative path
for synthesis: it reads the user's per-character provider choice
(``user_character_settings.voice_provider``), tier-gates it (free tier can't use
Fish, so it degrades to MiMo — still voice, never text), and returns the matching
row's voice_id / reference audio.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


@dataclass
class EffectiveVoice:
    """The voice a given user should hear for a character this turn."""

    provider: str  # 'mimo' | 'fish' | 'minimax'
    voice_type: str  # 'clone' | 'preset'
    voice_id: str | None  # fish model_id / minimax voice_id / preset's voice_id
    reference_ref: str | None  # mimo clone reference audio handle (clone_audio_url)


async def resolve_voice_id(
    character_id: str, db: AsyncSession, provider: str | None = None
) -> str | None:
    """Return the effective voice_id for a character, or None if unconfigured.

    Queries the character_voices table first; falls back to the in-process
    VOICE_CATALOG for built-in characters so existing behaviour is preserved.
    When ``provider`` is given, only that provider's row is considered;
    otherwise a ready clone is preferred over other rows.
    """
    where = "WHERE cv.character_id = :cid"
    params: dict = {"cid": character_id}
    if provider is not None:
        where += " AND cv.voice_provider = :prov"
        params["prov"] = provider

    result = await db.execute(
        text(f"""
            SELECT cv.voice_type, cv.clone_voice_id, cv.clone_status,
                   pv.voice_id AS preset_voice_id
            FROM character_voices cv
            LEFT JOIN preset_voices pv ON pv.id = cv.preset_voice_id
            {where}
            ORDER BY (cv.clone_status = 'ready') DESC, cv.voice_provider
            LIMIT 1
        """),
        params,
    )
    row = result.mappings().fetchone()

    if row is None:
        # No row — fall back to legacy in-memory catalog
        try:
            from heart.ss08_voice.voice_catalog import VoiceNotConfigured, get_voice_id

            return get_voice_id(character_id)
        except (KeyError, VoiceNotConfigured):
            return None

    if row["voice_type"] == "clone":
        if row["clone_status"] == "ready" and row["clone_voice_id"]:
            return row["clone_voice_id"]
        # Clone not ready — fall through to preset fallback
    if row["preset_voice_id"]:
        return row["preset_voice_id"]

    return None


async def resolve_voice_provider(character_id: str, db: AsyncSession) -> str | None:
    """Return a TTS provider that owns one of this character's voices.

    Legacy single-provider helper (kept for callers that don't have a user_id).
    With multiple provider rows it returns a ready one, preferring mimo. Prefer
    ``resolve_effective_voice`` for per-user synthesis routing.
    """
    result = await db.execute(
        text("""
            SELECT voice_provider FROM character_voices
            WHERE character_id = :cid
            ORDER BY (clone_status = 'ready') DESC,
                     (voice_provider = 'mimo') DESC,
                     voice_provider
            LIMIT 1
        """),
        {"cid": character_id},
    )
    provider = result.scalar_one_or_none()
    return provider or None


async def list_ready_voice_providers(character_id: str, db: AsyncSession) -> list[str]:
    """All providers with a ready voice row for this character (for the UI toggle)."""
    result = await db.execute(
        text("""
            SELECT voice_provider FROM character_voices
            WHERE character_id = :cid AND clone_status = 'ready'
            ORDER BY voice_provider
        """),
        {"cid": character_id},
    )
    return [r[0] for r in result.fetchall() if r[0]]


async def get_selected_voice_provider(
    character_id: str, user_id: uuid.UUID, db: AsyncSession
) -> str:
    """The user's chosen engine for this character (default 'mimo')."""
    result = await db.execute(
        text("""
            SELECT voice_provider FROM user_character_settings
            WHERE user_id = :uid AND character_id = :cid
        """),
        {"uid": user_id, "cid": character_id},
    )
    return result.scalar_one_or_none() or "mimo"


def _tts_allowed(tier: str, provider: str) -> bool:
    from heart.membership import get_entitlements

    return provider in get_entitlements(tier).tts


async def _ready_row(character_id: str, db: AsyncSession, provider: str) -> dict | None:
    result = await db.execute(
        text("""
            SELECT cv.voice_provider, cv.voice_type, cv.clone_voice_id, cv.clone_audio_url,
                   cv.clone_status, pv.voice_id AS preset_voice_id
            FROM character_voices cv
            LEFT JOIN preset_voices pv ON pv.id = cv.preset_voice_id
            WHERE cv.character_id = :cid AND cv.voice_provider = :prov
              AND cv.clone_status = 'ready'
            LIMIT 1
        """),
        {"cid": character_id, "prov": provider},
    )
    row = result.mappings().fetchone()
    return dict(row) if row else None


async def _all_ready_rows(character_id: str, db: AsyncSession) -> list[dict]:
    result = await db.execute(
        text("""
            SELECT cv.voice_provider, cv.voice_type, cv.clone_voice_id, cv.clone_audio_url,
                   cv.clone_status, pv.voice_id AS preset_voice_id
            FROM character_voices cv
            LEFT JOIN preset_voices pv ON pv.id = cv.preset_voice_id
            WHERE cv.character_id = :cid AND cv.clone_status = 'ready'
            ORDER BY (cv.voice_provider = 'mimo') DESC, cv.voice_provider
        """),
        {"cid": character_id},
    )
    return [dict(r) for r in result.mappings().fetchall()]


def _row_to_effective(row: dict) -> EffectiveVoice:
    is_clone = row["voice_type"] == "clone"
    voice_id = row["clone_voice_id"] if is_clone else row["preset_voice_id"]
    # MiMo clones are zero-shot: the reference audio IS the voice, so carry the
    # staged audio handle for the provider to base64-encode at synth time.
    reference = row["clone_audio_url"] if (is_clone and row["voice_provider"] == "mimo") else None
    return EffectiveVoice(
        provider=row["voice_provider"],
        voice_type=row["voice_type"],
        voice_id=voice_id,
        reference_ref=reference,
    )


async def resolve_effective_voice(
    character_id: str, user_id: uuid.UUID, db: AsyncSession
) -> EffectiveVoice | None:
    """Resolve which voice a user hears for a character this turn.

    Reads the user's per-character provider choice, tier-gates it (free tier
    can't use Fish → degrade to MiMo, still voice), and returns the matching
    ready row. Returns None only when no tier-allowed ready voice exists (the
    caller then keeps the turn text-only).
    """
    from heart.membership import get_effective_tier

    selected = await get_selected_voice_provider(character_id, user_id, db)
    tier = await get_effective_tier(db, user_id)

    provider = selected if _tts_allowed(tier, selected) else "mimo"

    row = await _ready_row(character_id, db, provider)
    if row is None:
        # Selected provider has no ready voice — fall back to any ready row the
        # tier is allowed to use (prefer mimo). Keeps voice working when only one
        # engine is configured, or the selection points at a missing clone.
        for candidate in await _all_ready_rows(character_id, db):
            if _tts_allowed(tier, candidate["voice_provider"]):
                row = candidate
                break

    if row is None:
        return None
    return _row_to_effective(row)


async def get_voice_config(
    character_id: str, db: AsyncSession, provider: str | None = None
) -> dict | None:
    """Return full voice config dict for a character, or None if unconfigured.

    When ``provider`` is given, returns that provider's row; otherwise prefers a
    ready row (deterministic single row even with multiple provider rows).
    """
    where = "WHERE cv.character_id = :cid"
    params: dict = {"cid": character_id}
    if provider is not None:
        where += " AND cv.voice_provider = :prov"
        params["prov"] = provider

    result = await db.execute(
        text(f"""
            SELECT cv.id, cv.voice_type, cv.preset_voice_id,
                   cv.clone_audio_url, cv.clone_voice_id, cv.clone_status,
                   cv.error_msg, cv.created_at, cv.voice_provider,
                   pv.name AS preset_name, pv.voice_id AS preset_voice_id_value,
                   pv.description AS preset_description
            FROM character_voices cv
            LEFT JOIN preset_voices pv ON pv.id = cv.preset_voice_id
            {where}
            ORDER BY (cv.clone_status = 'ready') DESC, cv.voice_provider
            LIMIT 1
        """),
        params,
    )
    row = result.mappings().fetchone()
    if row is None:
        return None
    return dict(row)
