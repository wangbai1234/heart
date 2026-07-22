"""Raw-SQL persistence for SS09 story mode.

Mirrors the non-ORM style used across the API layer (``text()`` + AsyncSession).
The caller owns the transaction (get_db commits per request).

PR1 scope: read paths for the scenario catalog. Run/message writes are added
alongside the story engine (PR3).
"""

from __future__ import annotations

import json
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Scenario, ScenarioCard


def _jsonb(value: Any) -> dict[str, Any]:
    """Normalize a JSONB object column that may arrive as dict or str.

    Story JSONB columns here (player_template_json / player_identity_json) are
    always JSON objects; anything else (str that isn't an object, list, null)
    degrades to an empty dict.
    """
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _card_from_row(row: Any, *, age_verified: bool) -> ScenarioCard:
    locked = row.maturity == "adult" and not age_verified
    return ScenarioCard(
        id=row.id,
        title=row.title,
        genre=row.genre,
        cover_url=row.cover_url,
        # Never leak adult blurbs to unverified viewers; show a gate hint.
        blurb=("🔞 需完成年龄验证后查看" if locked else row.blurb),
        maturity=row.maturity,
        is_featured=row.is_featured,
        play_count=row.play_count,
        locked=locked,
    )


async def list_scenarios(
    session: AsyncSession,
    *,
    genre: Optional[str] = None,
    featured: Optional[bool] = None,
    age_verified: bool = False,
    limit: int = 30,
    offset: int = 0,
) -> list[ScenarioCard]:
    """List published scenarios as browse cards, most-played first."""
    clauses = ["status = 'published'"]
    params: dict[str, Any] = {"limit": max(1, min(limit, 100)), "offset": max(0, offset)}
    if genre:
        clauses.append("genre = :genre")
        params["genre"] = genre
    if featured is not None:
        clauses.append("is_featured = :featured")
        params["featured"] = featured
    where = " AND ".join(clauses)
    result = await session.execute(
        text(
            f"""
            SELECT id, title, genre, cover_url, blurb, maturity, is_featured, play_count
            FROM story_scenarios
            WHERE {where}
            ORDER BY is_featured DESC, play_count DESC, created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    )
    return [_card_from_row(r, age_verified=age_verified) for r in result.fetchall()]


async def list_genres(session: AsyncSession) -> list[dict[str, Any]]:
    """Distinct genres of published scenarios with counts (for filter chips)."""
    result = await session.execute(
        text(
            """
            SELECT genre, COUNT(*) AS n
            FROM story_scenarios
            WHERE status = 'published'
            GROUP BY genre
            ORDER BY n DESC
            """
        )
    )
    # NB: alias is `n`, not `count` — Row.count is the tuple method and shadows
    # a column of that name.
    return [{"genre": r.genre, "count": int(r.n)} for r in result.fetchall()]


async def get_scenario(session: AsyncSession, scenario_id: UUID) -> Optional[Scenario]:
    """Fetch a single published scenario by id (any status: caller filters)."""
    result = await session.execute(
        text(
            """
            SELECT id, slug, title, genre, cover_url, blurb, maturity,
                   gm_system_prompt, player_template_json, status, is_featured, play_count
            FROM story_scenarios
            WHERE id = :id
            """
        ),
        {"id": str(scenario_id)},
    )
    row = result.fetchone()
    if row is None:
        return None
    return Scenario(
        id=row.id,
        slug=row.slug,
        title=row.title,
        genre=row.genre,
        cover_url=row.cover_url,
        blurb=row.blurb,
        maturity=row.maturity,
        gm_system_prompt=row.gm_system_prompt,
        player_template_json=_jsonb(row.player_template_json),
        status=row.status,
        is_featured=row.is_featured,
        play_count=row.play_count,
    )
