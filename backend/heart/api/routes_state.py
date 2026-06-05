"""
State Inspect API — read-only endpoints for CLI state inspection.

Provides endpoints for CLI to inspect:
- Emotion state
- Relationship state
- Inner state
- Memory (recent episodes, L3 facts, L4 identity)
- Proactive messages

All endpoints are read-only and require user_id query param.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.api.wiring import get_db, get_emotion_service, get_inner_state_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/state", tags=["state-inspect"])


@router.get("/emotion")
async def get_emotion_state(
    user_id: UUID = Query(..., description="User UUID"),
    character_id: str = Query("rin", description="Character ID"),
):
    """Get current emotion state for user×character."""
    svc = get_emotion_service()
    if svc is None:
        return {"error": "EmotionService not available"}

    block = await svc.get_context_block(user_id, character_id)
    return {
        "user_id": str(user_id),
        "character_id": character_id,
        "vad": block.get("vad", {}),
        "active_emotions": block.get("active_emotions", []),
        "emotion_summary": block.get("emotion_summary", ""),
        "mood_descriptor": block.get("mood_descriptor", ""),
        "energy_descriptor": block.get("energy_descriptor", ""),
    }


@router.get("/relationship")
async def get_relationship_state(
    user_id: UUID = Query(..., description="User UUID"),
    character_id: str = Query("rin", description="Character ID"),
    db_session: AsyncSession = Depends(get_db),
):
    """Get current relationship state for user×character."""
    try:
        result = await db_session.execute(
            text(
                "SELECT current_stage, trust_score, attachment_strength, "
                "intimacy_level, total_interactions, longest_continuous_streak_days "
                "FROM relationship_states "
                "WHERE user_id = :user_id AND character_id = :character_id"
            ),
            {"user_id": str(user_id), "character_id": character_id},
        )
        row = result.fetchone()

        if row is None:
            return {
                "user_id": str(user_id),
                "character_id": character_id,
                "phase": "stranger",
                "trust": 0.0,
                "attachment": "secure",
                "intimacy": 0.0,
                "total_interactions": 0,
            }

        return {
            "user_id": str(user_id),
            "character_id": character_id,
            "phase": row[0] or "stranger",
            "trust": float(row[1] or 0.0),
            "attachment": str(row[2] or "secure"),
            "intimacy": float(row[3] or 0.0),
            "total_interactions": int(row[4] or 0),
            "longest_streak_days": int(row[5] or 0),
        }
    except Exception as e:
        logger.exception("get_relationship_state_failed")
        return {"error": str(e)}


@router.get("/inner")
async def get_inner_state(
    user_id: UUID = Query(..., description="User UUID"),
    character_id: str = Query("rin", description="Character ID"),
):
    """Get current inner state for user×character."""
    svc = get_inner_state_service()
    if svc is None:
        return {"error": "InnerStateService not available"}

    state = svc.get_inner_state(user_id, character_id)
    if state is None:
        return {
            "user_id": str(user_id),
            "character_id": character_id,
            "mood": 0.5,
            "energy": 0.6,
            "ticks_today": 0,
            "proactives_today": 0,
        }

    return {
        "user_id": str(user_id),
        "character_id": character_id,
        "mood": state.mood,
        "energy": state.energy,
        "ticks_today": state.ticks_today,
        "proactives_today": state.proactives_today,
        "last_tick_at": state.last_tick_at.isoformat() if state.last_tick_at else None,
    }


memory_router = APIRouter(prefix="/api/memory", tags=["memory-inspect"])


@memory_router.get("/recent")
async def get_recent_memories(
    user_id: UUID = Query(..., description="User UUID"),
    character_id: str = Query("rin", description="Character ID"),
    limit: int = Query(10, description="Max episodes to return"),
    db_session: AsyncSession = Depends(get_db),
):
    """Get recent L2 episodes and L3 facts."""
    try:
        # Get recent L2 episodes
        episodes_result = await db_session.execute(
            text(
                "SELECT id, summary, emotional_peak_valence, created_at "
                "FROM episodic_memories "
                "WHERE user_id = :user_id AND character_id = :character_id "
                "ORDER BY created_at DESC LIMIT :limit"
            ),
            {"user_id": str(user_id), "character_id": character_id, "limit": limit},
        )
        episodes = [
            {
                "id": str(row[0]),
                "summary": row[1],
                "emotional_peak": float(row[2] or 0.0),
                "created_at": row[3].isoformat() if row[3] else None,
            }
            for row in episodes_result.fetchall()
        ]

        # Get recent L3 facts
        facts_result = await db_session.execute(
            text(
                "SELECT id, predicate, subject, object, importance, confidence "
                "FROM fact_nodes "
                "WHERE user_id = :user_id AND character_id = :character_id "
                "AND NOT do_not_recall "
                "ORDER BY importance DESC LIMIT :limit"
            ),
            {"user_id": str(user_id), "character_id": character_id, "limit": limit},
        )
        facts = [
            {
                "id": str(row[0]),
                "predicate": row[1],
                "subject": row[2],
                "object": row[3],
                "importance": float(row[4] or 0.0),
                "confidence": float(row[5] or 0.0),
            }
            for row in facts_result.fetchall()
        ]

        return {
            "user_id": str(user_id),
            "character_id": character_id,
            "episodes": episodes,
            "facts": facts,
        }
    except Exception as e:
        logger.exception("get_recent_memories_failed")
        return {"error": str(e)}


@memory_router.get("/l4")
async def get_l4_identity(
    user_id: UUID = Query(..., description="User UUID"),
    character_id: str = Query("rin", description="Character ID"),
    db_session: AsyncSession = Depends(get_db),
):
    """Get L4 identity memories (她记得的我)."""
    try:
        result = await db_session.execute(
            text(
                "SELECT id, key, value, category, sacred_reason, created_at "
                "FROM identity_memories "
                "WHERE user_id = :user_id AND character_id = :character_id "
                "ORDER BY created_at DESC"
            ),
            {"user_id": str(user_id), "character_id": character_id},
        )
        memories = [
            {
                "id": str(row[0]),
                "key": row[1],
                "value": row[2],
                "category": row[3],
                "reason": row[4],
                "created_at": row[5].isoformat() if row[5] else None,
            }
            for row in result.fetchall()
        ]

        return {
            "user_id": str(user_id),
            "character_id": character_id,
            "count": len(memories),
            "memories": memories,
        }
    except Exception as e:
        logger.exception("get_l4_identity_failed")
        return {"error": str(e)}


dev_router = APIRouter(prefix="/api/dev", tags=["dev-tools"])


@dev_router.post("/jump_phase")
async def jump_phase(
    user_id: UUID = Query(..., description="User UUID"),
    character_id: str = Query("rin", description="Character ID"),
    phase: int = Query(..., description="Target phase (1-7)"),
    db_session: AsyncSession = Depends(get_db),
):
    """Jump to a specific relationship phase (dev mode only)."""
    import os

    if os.getenv("HEART_DEV_MODE", "").lower() != "true":
        return {"error": "Dev mode not enabled"}

    stage_map = {
        1: "stranger",
        2: "acquaintance",
        3: "friend",
        4: "confidant",
        5: "romantic_interest",
        6: "lover",
        7: "bonded",
    }

    target_stage = stage_map.get(phase)
    if target_stage is None:
        return {"error": f"Invalid phase {phase}. Must be 1-7."}

    try:
        await db_session.execute(
            text(
                "UPDATE relationship_states SET current_stage = :stage, updated_at = NOW() "
                "WHERE user_id = :user_id AND character_id = :character_id"
            ),
            {"user_id": str(user_id), "character_id": character_id, "stage": target_stage},
        )
        await db_session.commit()

        return {
            "user_id": str(user_id),
            "character_id": character_id,
            "jumped_to": target_stage,
            "phase_number": phase,
        }
    except Exception as e:
        logger.exception("jump_phase_failed")
        return {"error": str(e)}


@dev_router.post("/sleep")
async def dev_sleep(
    user_id: UUID = Query(..., description="User UUID"),
    character_id: str = Query("rin", description="Character ID"),
    hours: int = Query(24, description="Hours to fast-forward"),
    db_session: AsyncSession = Depends(get_db),
):
    """Fast-forward time by N hours (triggers decay + inner loop tick)."""
    import os

    if os.getenv("HEART_DEV_MODE", "").lower() != "true":
        return {"error": "Dev mode not enabled"}

    try:
        # Update last_activity_at to simulate time passing
        await db_session.execute(
            text(
                "UPDATE sessions SET last_activity_at = last_activity_at - INTERVAL ':hours hours' "
                "WHERE user_id = :user_id AND character_id = :character_id"
            ),
            {"user_id": str(user_id), "character_id": character_id, "hours": hours},
        )
        await db_session.commit()

        # Trigger inner state tick with simulated time
        from heart.ss06_inner_state.service import InnerStateService

        svc = InnerStateService()
        svc.tick(
            user_id=user_id,
            character_id=character_id,
            days_since_last_interaction=hours / 24.0,
        )

        return {
            "user_id": str(user_id),
            "character_id": character_id,
            "hours_slept": hours,
            "message": f"Time fast-forwarded {hours}h. Decay triggered, inner loop ticked.",
        }
    except Exception as e:
        logger.exception("dev_sleep_failed")
        return {"error": str(e)}


@dev_router.post("/coldwar")
async def dev_coldwar(
    user_id: UUID = Query(..., description="User UUID"),
    character_id: str = Query("rin", description="Character ID"),
    active: bool = Query(True, description="Activate or deactivate cold war"),
    db_session: AsyncSession = Depends(get_db),
):
    """Force cold war state on/off (dev mode only)."""
    import os

    if os.getenv("HEART_DEV_MODE", "").lower() != "true":
        return {"error": "Dev mode not enabled"}

    try:
        # Update relationship state
        if active:
            await db_session.execute(
                text(
                    "UPDATE relationship_states SET current_stage = 'cold_war', updated_at = NOW() "
                    "WHERE user_id = :user_id AND character_id = :character_id"
                ),
                {"user_id": str(user_id), "character_id": character_id},
            )
        else:
            await db_session.execute(
                text(
                    "UPDATE relationship_states SET current_stage = 'friend', updated_at = NOW() "
                    "WHERE user_id = :user_id AND character_id = :character_id"
                ),
                {"user_id": str(user_id), "character_id": character_id},
            )
        await db_session.commit()

        return {
            "user_id": str(user_id),
            "character_id": character_id,
            "cold_war_active": active,
        }
    except Exception as e:
        logger.exception("dev_coldwar_failed")
        return {"error": str(e)}
