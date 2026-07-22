"""Story/剧情 mode REST API.

Read paths for the scenario catalog, plus run lifecycle (start/list/resume/
delete). The real-time turn WebSocket lives in routes_story_ws.py.

Scenarios are NOT access-gated by age: registration already restricts signup to
adults, so ``maturity`` is a display-only label (🔞) — the UI shows it on the
card/intro but never locks the scenario.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from heart.api.rate_limit import limiter
from heart.api.wiring import get_db, get_story_service
from heart.core.auth import TokenData, get_current_user
from heart.ss09_story import repository as repo
from heart.ss09_story.models import DEFAULT_PLAYER_TEMPLATE

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/story", tags=["story"])


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
    cards = await repo.list_scenarios(
        db,
        genre=genre,
        featured=featured,
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
    """Scenario detail. Never leaks the GM prompt. ``maturity`` is a display-only
    label (🔞) — scenarios are not age-gated.
    """
    scenario = await repo.get_scenario(db, scenario_id)
    if scenario is None or scenario.status != "published":
        raise HTTPException(404, "scenario_not_found")

    template = scenario.player_template_json or DEFAULT_PLAYER_TEMPLATE
    return {
        "id": str(scenario.id),
        "title": scenario.title,
        "genre": scenario.genre,
        "cover_url": scenario.cover_url,
        "blurb": scenario.blurb,
        "maturity": scenario.maturity,
        "is_featured": scenario.is_featured,
        "play_count": scenario.play_count,
        # Player card template drives the StartRunSheet form.
        "player_template": template,
    }


# ── Run lifecycle (PR3) ─────────────────────────────────────────────


class StartRunBody(BaseModel):
    scenario_id: uuid.UUID
    player_identity: dict[str, Any] = Field(default_factory=dict)


def _bubble_dto(b: Any) -> dict[str, Any]:
    """Serialize a persisted story message row / bubble for the client."""
    return {
        "id": str(b.id),
        "turn_id": str(b.turn_id),
        "seq": b.seq,
        "role": b.role,
        "kind": b.kind,
        "npc_name": b.npc_name,
        "content": b.content,
    }


def _run_dto(run: Any) -> dict[str, Any]:
    return {
        "run_id": str(run.id),
        "scenario_id": str(run.scenario_id),
        "title": run.title,
        "status": run.status,
        "turn_count": run.turn_count,
        "model": run.model,
        "created_at": run.created_at.isoformat(),
        "last_activity_at": run.last_activity_at.isoformat(),
    }


@router.post("/runs")
@limiter.limit("20/minute")
async def start_run(
    request: Request,
    body: StartRunBody,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Start a new run and return the opening GM bubbles."""
    scenario = await repo.get_scenario(db, body.scenario_id)
    if scenario is None or scenario.status != "published":
        raise HTTPException(404, "scenario_not_found")

    service = get_story_service()
    if service is None:
        raise HTTPException(503, "story_engine_unavailable")

    try:
        result = await service.start_run(
            user_id=uuid.UUID(current_user.user_id),
            scenario=scenario,
            player_identity=body.player_identity,
        )
    except Exception as e:
        logger.exception("story_start_run_failed", scenario_id=str(body.scenario_id))
        raise HTTPException(502, "story_opening_failed") from e

    return {
        "run": _run_dto(result.run),
        "opening_bubbles": [
            {
                "turn_id": None,
                "kind": b["kind"],
                "npc_name": b.get("npc_name"),
                "content": b["content"],
            }
            for b in result.opening_bubbles
        ],
    }


@router.get("/runs")
@limiter.limit("60/minute")
async def list_runs(
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List the caller's runs (active first)."""
    runs = await repo.list_runs(db, uuid.UUID(current_user.user_id))
    return {"runs": [_run_dto(r) for r in runs]}


@router.get("/runs/{run_id}")
@limiter.limit("60/minute")
async def get_run(
    request: Request,
    run_id: uuid.UUID,
    after_seq: int = Query(0, ge=0),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Resume: run metadata + paginated transcript (ascending seq)."""
    user_id = uuid.UUID(current_user.user_id)
    run = await repo.get_run(db, run_id, user_id)
    if run is None:
        raise HTTPException(404, "run_not_found")
    messages = await repo.list_messages(db, run_id, after_seq=after_seq)
    return {
        "run": _run_dto(run),
        "player_identity": run.player_identity_json,
        "messages": [_bubble_dto(m) for m in messages],
    }


@router.delete("/runs/{run_id}")
@limiter.limit("30/minute")
async def delete_run(
    request: Request,
    run_id: uuid.UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Logical-delete a run (status='deleted')."""
    ok = await repo.soft_delete_run(db, run_id, uuid.UUID(current_user.user_id))
    if not ok:
        raise HTTPException(404, "run_not_found")
    return {"ok": True}
