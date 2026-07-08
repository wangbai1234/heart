"""DB access layer for the soul_specs table (migration 020).

All functions accept a SQLAlchemy async Connection and use raw SQL to stay
consistent with the rest of the project.  Callers are responsible for
transaction management; these helpers do not commit.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

_AnyDB = AsyncConnection | AsyncSession


async def fetch_active_specs(db: _AnyDB) -> list[dict[str, Any]]:
    """Return all rows where status='active', ordered by created_at."""
    result = await db.execute(
        text(
            "SELECT character_id, spec_version, source, spec, draft, created_at"
            " FROM soul_specs WHERE status = 'active'"
            " ORDER BY created_at ASC"
        )
    )
    return [dict(row._mapping) for row in result.fetchall()]


async def fetch_active_spec(db: _AnyDB, character_id: str) -> dict[str, Any] | None:
    """Return the single active spec row for a character, or None."""
    result = await db.execute(
        text(
            "SELECT character_id, spec_version, source, spec, draft, created_at"
            " FROM soul_specs"
            " WHERE character_id = :cid AND status = 'active'"
            " LIMIT 1"
        ),
        {"cid": character_id},
    )
    row = result.fetchone()
    return dict(row._mapping) if row else None


async def insert_spec(
    db: _AnyDB,
    *,
    character_id: str,
    spec_version: str,
    source: str = "ugc",
    spec: dict[str, Any],
    draft: dict[str, Any] | None = None,
) -> None:
    """Insert a new soul_specs row with status='active'."""
    await db.execute(
        text(
            "INSERT INTO soul_specs"
            " (character_id, spec_version, source, status, spec, draft)"
            " VALUES (:cid, :ver, :src, 'active', :spec, :draft)"
        ),
        {
            "cid": character_id,
            "ver": spec_version,
            "src": source,
            "spec": json.dumps(spec),
            "draft": json.dumps(draft) if draft is not None else None,
        },
    )


async def supersede_active(db: _AnyDB, character_id: str) -> None:
    """Mark all active rows for a character as superseded."""
    await db.execute(
        text(
            "UPDATE soul_specs SET status = 'superseded'"
            " WHERE character_id = :cid AND status = 'active'"
        ),
        {"cid": character_id},
    )


async def set_spec_status(
    db: _AnyDB,
    character_id: str,
    spec_version: str,
    status: str,
) -> None:
    """Set the status of a specific (character_id, spec_version) row."""
    await db.execute(
        text(
            "UPDATE soul_specs SET status = :status"
            " WHERE character_id = :cid AND spec_version = :ver"
        ),
        {"status": status, "cid": character_id, "ver": spec_version},
    )
