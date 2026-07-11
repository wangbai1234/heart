"""DB-driven voice resolver — replaces hardcoded VOICE_CATALOG for UGC characters.

Priority:
  1. character_voices row (DB, covers both preset and clone)
  2. voice_catalog.py legacy lookup (built-in rin/dorothy fallback)
"""

from __future__ import annotations

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


async def resolve_voice_id(character_id: str, db: AsyncSession) -> str | None:
    """Return the effective voice_id for a character, or None if unconfigured.

    Queries the character_voices table first; falls back to the in-process
    VOICE_CATALOG for built-in characters so existing behaviour is preserved.
    """
    result = await db.execute(
        text("""
            SELECT cv.voice_type, cv.clone_voice_id, cv.clone_status,
                   pv.voice_id AS preset_voice_id
            FROM character_voices cv
            LEFT JOIN preset_voices pv ON pv.id = cv.preset_voice_id
            WHERE cv.character_id = :cid
        """),
        {"cid": character_id},
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


async def get_voice_config(character_id: str, db: AsyncSession) -> dict | None:
    """Return full voice config dict for a character, or None if unconfigured."""
    result = await db.execute(
        text("""
            SELECT cv.id, cv.voice_type, cv.preset_voice_id,
                   cv.clone_audio_url, cv.clone_voice_id, cv.clone_status,
                   cv.error_msg, cv.created_at,
                   pv.name AS preset_name, pv.voice_id AS preset_voice_id_value,
                   pv.description AS preset_description
            FROM character_voices cv
            LEFT JOIN preset_voices pv ON pv.id = cv.preset_voice_id
            WHERE cv.character_id = :cid
        """),
        {"cid": character_id},
    )
    row = result.mappings().fetchone()
    if row is None:
        return None
    return dict(row)
