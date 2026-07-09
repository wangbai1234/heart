"""DB access layer for the character_content table (migration 021).

Raw SQL helpers following the same pattern as spec_store.py.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

_AnyDB = AsyncConnection | AsyncSession


async def fetch_all_content(db: _AnyDB) -> list[dict[str, Any]]:
    """Return all rows from character_content."""
    result = await db.execute(
        text(
            "SELECT character_id, proactive_persona, proactive_templates,"
            " ritual_morning, ritual_night FROM character_content"
        )
    )
    return [dict(row._mapping) for row in result.fetchall()]


async def upsert_content(
    db: _AnyDB,
    *,
    character_id: str,
    proactive_persona: str = "",
    proactive_templates: list[str] | None = None,
    ritual_morning: str = "",
    ritual_night: str = "",
) -> None:
    """Insert or replace character content for a UGC character."""
    await db.execute(
        text(
            "INSERT INTO character_content"
            " (character_id, proactive_persona, proactive_templates, ritual_morning, ritual_night)"
            " VALUES (:cid, :persona, :templates, :morning, :night)"
            " ON CONFLICT (character_id) DO UPDATE SET"
            "  proactive_persona = EXCLUDED.proactive_persona,"
            "  proactive_templates = EXCLUDED.proactive_templates,"
            "  ritual_morning = EXCLUDED.ritual_morning,"
            "  ritual_night = EXCLUDED.ritual_night,"
            "  updated_at = NOW()"
        ),
        {
            "cid": character_id,
            "persona": proactive_persona,
            "templates": proactive_templates or [],
            "morning": ritual_morning,
            "night": ritual_night,
        },
    )


async def delete_content(db: _AnyDB, character_id: str) -> None:
    """Delete content row for a character."""
    await db.execute(
        text("DELETE FROM character_content WHERE character_id = :cid"),
        {"cid": character_id},
    )
