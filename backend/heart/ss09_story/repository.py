"""Raw-SQL persistence for SS09 story mode.

Mirrors the non-ORM style used across the API layer (``text()`` + AsyncSession).
The caller owns the transaction (get_db commits per request).

PR1 scope: read paths for the scenario catalog. Run/message writes are added
alongside the story engine (PR3).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Run, Scenario, ScenarioCard, StoryMessage


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


def _card_from_row(row: Any) -> ScenarioCard:
    # `maturity` is a display-only label (🔞); registration already restricts
    # signup to adults, so scenarios are never access-gated here.
    return ScenarioCard(
        id=row.id,
        title=row.title,
        genre=row.genre,
        cover_url=row.cover_url,
        blurb=row.blurb,
        maturity=row.maturity,
        is_featured=row.is_featured,
        play_count=row.play_count,
    )


async def list_scenarios(
    session: AsyncSession,
    *,
    genre: Optional[str] = None,
    featured: Optional[bool] = None,
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
    return [_card_from_row(r) for r in result.fetchall()]


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


# ── Run + message writes (PR3 story engine) ─────────────────────────


def _run_from_row(row: Any) -> Run:
    return Run(
        id=row.id,
        user_id=row.user_id,
        scenario_id=row.scenario_id,
        player_identity_json=_jsonb(row.player_identity_json),
        title=row.title,
        summary=row.summary,
        summary_watermark=row.summary_watermark,
        turn_count=row.turn_count,
        status=row.status,
        model=row.model,
        created_at=row.created_at,
        last_activity_at=row.last_activity_at,
    )


def _message_from_row(row: Any) -> StoryMessage:
    return StoryMessage(
        id=row.id,
        run_id=row.run_id,
        turn_id=row.turn_id,
        seq=row.seq,
        role=row.role,
        kind=row.kind,
        npc_name=row.npc_name,
        content=row.content,
        created_at=row.created_at,
    )


async def create_run(
    session: AsyncSession,
    *,
    user_id: UUID,
    scenario_id: UUID,
    player_identity: dict[str, Any],
    title: str,
    model: str,
) -> Run:
    """Insert a new run and bump the scenario's play_count (same txn)."""
    result = await session.execute(
        text(
            """
            INSERT INTO story_runs
                (user_id, scenario_id, player_identity_json, title, model)
            VALUES
                (:user_id, :scenario_id, CAST(:identity AS JSONB), :title, :model)
            RETURNING id, user_id, scenario_id, player_identity_json, title,
                      summary, summary_watermark, turn_count, status, model,
                      created_at, last_activity_at
            """
        ),
        {
            "user_id": str(user_id),
            "scenario_id": str(scenario_id),
            "identity": json.dumps(player_identity, ensure_ascii=False),
            "title": title,
            "model": model,
        },
    )
    row = result.fetchone()
    await session.execute(
        text("UPDATE story_scenarios SET play_count = play_count + 1 WHERE id = :sid"),
        {"sid": str(scenario_id)},
    )
    return _run_from_row(row)


async def get_run(session: AsyncSession, run_id: UUID, user_id: UUID) -> Optional[Run]:
    """Fetch a run scoped to its owner (never leak another user's run)."""
    result = await session.execute(
        text(
            """
            SELECT id, user_id, scenario_id, player_identity_json, title,
                   summary, summary_watermark, turn_count, status, model,
                   created_at, last_activity_at
            FROM story_runs
            WHERE id = :id AND user_id = :uid AND status != 'deleted'
            """
        ),
        {"id": str(run_id), "uid": str(user_id)},
    )
    row = result.fetchone()
    return _run_from_row(row) if row else None


async def list_runs(session: AsyncSession, user_id: UUID) -> list[Run]:
    """List a user's non-deleted runs, active first, most-recent first."""
    result = await session.execute(
        text(
            """
            SELECT id, user_id, scenario_id, player_identity_json, title,
                   summary, summary_watermark, turn_count, status, model,
                   created_at, last_activity_at
            FROM story_runs
            WHERE user_id = :uid AND status != 'deleted'
            ORDER BY (status = 'active') DESC, last_activity_at DESC
            LIMIT 100
            """
        ),
        {"uid": str(user_id)},
    )
    return [_run_from_row(r) for r in result.fetchall()]


async def soft_delete_run(session: AsyncSession, run_id: UUID, user_id: UUID) -> bool:
    """Logical-delete a run. Returns True if a row was affected."""
    result = await session.execute(
        text(
            """
            UPDATE story_runs SET status = 'deleted'
            WHERE id = :id AND user_id = :uid AND status != 'deleted'
            """
        ),
        {"id": str(run_id), "uid": str(user_id)},
    )
    return (getattr(result, "rowcount", 0) or 0) > 0


async def recent_messages(
    session: AsyncSession, run_id: UUID, limit: int = 16
) -> list[StoryMessage]:
    """Most recent messages for a run, returned in ascending seq order."""
    result = await session.execute(
        text(
            """
            SELECT * FROM (
                SELECT id, run_id, turn_id, seq, role, kind, npc_name, content, created_at
                FROM story_messages
                WHERE run_id = :rid
                ORDER BY seq DESC
                LIMIT :limit
            ) sub
            ORDER BY seq ASC
            """
        ),
        {"rid": str(run_id), "limit": max(1, limit)},
    )
    return [_message_from_row(r) for r in result.fetchall()]


async def list_messages(
    session: AsyncSession, run_id: UUID, after_seq: int = 0, limit: int = 200
) -> list[StoryMessage]:
    """Paginated transcript for resume, ascending seq."""
    result = await session.execute(
        text(
            """
            SELECT id, run_id, turn_id, seq, role, kind, npc_name, content, created_at
            FROM story_messages
            WHERE run_id = :rid AND seq > :after
            ORDER BY seq ASC
            LIMIT :limit
            """
        ),
        {"rid": str(run_id), "after": after_seq, "limit": max(1, min(limit, 500))},
    )
    return [_message_from_row(r) for r in result.fetchall()]


async def next_seq(session: AsyncSession, run_id: UUID) -> int:
    """Return the next monotonic seq for a run (max+1, starting at 1)."""
    result = await session.execute(
        text("SELECT COALESCE(MAX(seq), 0) AS m FROM story_messages WHERE run_id = :rid"),
        {"rid": str(run_id)},
    )
    return int(result.scalar_one()) + 1


async def add_message(
    session: AsyncSession,
    *,
    run_id: UUID,
    user_id: UUID,
    turn_id: UUID,
    seq: int,
    role: str,
    kind: str,
    content: str,
    npc_name: Optional[str] = None,
) -> StoryMessage:
    """Insert one story message row."""
    result = await session.execute(
        text(
            """
            INSERT INTO story_messages
                (run_id, user_id, turn_id, seq, role, kind, npc_name, content)
            VALUES
                (:run_id, :user_id, :turn_id, :seq, :role, :kind, :npc_name, :content)
            RETURNING id, run_id, turn_id, seq, role, kind, npc_name, content, created_at
            """
        ),
        {
            "run_id": str(run_id),
            "user_id": str(user_id),
            "turn_id": str(turn_id),
            "seq": seq,
            "role": role,
            "kind": kind,
            "npc_name": npc_name,
            "content": content,
        },
    )
    return _message_from_row(result.fetchone())


async def bump_run_activity(
    session: AsyncSession,
    run_id: UUID,
    *,
    turns_delta: int = 0,
    summary: Optional[str] = None,
    summary_watermark: Optional[int] = None,
) -> None:
    """Advance last_activity_at, optionally turn_count and summary state."""
    sets = ["last_activity_at = :now", "turn_count = turn_count + :turns_delta"]
    params: dict[str, Any] = {
        "id": str(run_id),
        "now": datetime.now(timezone.utc),
        "turns_delta": turns_delta,
    }
    if summary is not None:
        sets.append("summary = :summary")
        params["summary"] = summary
    if summary_watermark is not None:
        sets.append("summary_watermark = :wm")
        params["wm"] = summary_watermark
    await session.execute(
        text(f"UPDATE story_runs SET {', '.join(sets)} WHERE id = :id"),
        params,
    )
