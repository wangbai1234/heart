"""Story/剧情 mode REST API.

Read paths for the scenario catalog (PR1). Run lifecycle (start/list/resume/
delete) and the real-time turn WebSocket are added in PR3.

Adult scenarios (maturity='adult') are gated by the existing age-gate
(users.age_verified_at). List/detail responses soft-lock them for unverified
users (``locked: true``) rather than hard-failing, so the UI can drive the user
to /age-gate; start-run + the WS enforce verification server-side (PR3).
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.api.rate_limit import limiter
from heart.api.wiring import get_db
from heart.core.auth import TokenData, get_current_user
from heart.ss09_story import repository as repo
from heart.ss09_story.models import DEFAULT_PLAYER_TEMPLATE

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/story", tags=["story"])


async def _is_age_verified(db: AsyncSession, user_id: str) -> bool:
    """Non-raising age-gate check (contrast deps.require_age_verified)."""
    result = await db.execute(
        text("SELECT age_verified_at FROM users WHERE id = :uid"),
        {"uid": uuid.UUID(user_id)},
    )
    return result.scalar_one_or_none() is not None


@router.get("/scenarios")
@limiter.limit("60/minute")
async def list_scenarios(
    request: Request,
    genre: Optional[str] = Query(None, description="题材筛选"),
    featured: Optional[bool] = Query(None, description="仅精选"),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Browse published scenarios as cards."""
    age_verified = await _is_age_verified(db, current_user.user_id)
    cards = await repo.list_scenarios(
        db,
        genre=genre,
        featured=featured,
        age_verified=age_verified,
        limit=limit,
        offset=offset,
    )
    return {
        "count": len(cards),
        "scenarios": [
            {
                "id": str(c.id),
                "title": c.title,
                "genre": c.genre,
                "cover_url": c.cover_url,
                "blurb": c.blurb,
                "maturity": c.maturity,
                "is_featured": c.is_featured,
                "play_count": c.play_count,
                "locked": c.locked,
            }
            for c in cards
        ],
    }


@router.get("/genres")
@limiter.limit("60/minute")
async def list_genres(
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Distinct genres of published scenarios with counts (filter chips)."""
    genres = await repo.list_genres(db)
    return {"genres": genres}


@router.get("/scenarios/{scenario_id}")
@limiter.limit("60/minute")
async def get_scenario(
    request: Request,
    scenario_id: uuid.UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Scenario detail. Never leaks the GM prompt; adult scenarios are locked
    for unverified viewers (blurb/npc hidden), which drives the age-gate flow.
    """
    scenario = await repo.get_scenario(db, scenario_id)
    if scenario is None or scenario.status != "published":
        raise HTTPException(404, "scenario_not_found")

    age_verified = await _is_age_verified(db, current_user.user_id)
    locked = scenario.maturity == "adult" and not age_verified

    template = scenario.player_template_json or DEFAULT_PLAYER_TEMPLATE
    return {
        "id": str(scenario.id),
        "title": scenario.title,
        "genre": scenario.genre,
        "cover_url": scenario.cover_url,
        "blurb": ("🔞 需完成年龄验证后查看" if locked else scenario.blurb),
        "maturity": scenario.maturity,
        "is_featured": scenario.is_featured,
        "play_count": scenario.play_count,
        "locked": locked,
        # Player card template drives the StartRunSheet form.
        "player_template": template,
    }
