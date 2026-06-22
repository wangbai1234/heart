"""
State Inspect API — read-only endpoints for CLI state inspection.

Provides endpoints for CLI to inspect:
- Emotion state
- Relationship state
- Inner state
- Memory (recent episodes, L3 facts, L4 identity)
- Proactive messages

All endpoints are read-only, require auth, and require user_id query param.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.api.wiring import get_db, get_emotion_service, get_inner_state_service
from heart.core.auth import TokenData, get_current_user

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/state", tags=["state-inspect"])


@router.get("/emotion")
async def get_emotion_state(
    user_id: UUID = Query(..., description="User UUID"),
    character_id: str = Query("rin", description="Character ID"),
    current_user: TokenData = Depends(get_current_user),
):
    """Get current emotion state for user×character."""
    if str(current_user.user_id) != str(user_id):
        raise HTTPException(403, "Cannot read another user's state")
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
    current_user: TokenData = Depends(get_current_user),
):
    """Get current relationship state for user×character."""
    if str(current_user.user_id) != str(user_id):
        raise HTTPException(403, "Cannot read another user's state")
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
        logger.debug("get_relationship_state_failed", error=str(e))
        return {
            "user_id": str(user_id),
            "character_id": character_id,
            "phase": "stranger",
            "trust": 0.0,
            "attachment": "secure",
            "intimacy": 0.0,
            "total_interactions": 0,
        }


@router.get("/inner")
async def get_inner_state(
    user_id: UUID = Query(..., description="User UUID"),
    character_id: str = Query("rin", description="Character ID"),
    current_user: TokenData = Depends(get_current_user),
):
    """Get current inner state for user×character."""
    if str(current_user.user_id) != str(user_id):
        raise HTTPException(403, "Cannot read another user's state")
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
    current_user: TokenData = Depends(get_current_user),
):
    """Get recent L2 episodes and L3 facts."""
    if str(current_user.user_id) != str(user_id):
        raise HTTPException(403, "Cannot read another user's memory")
    """Get recent L2 episodes and L3 facts."""
    episodes = []
    facts = []

    try:
        # Get recent L2 episodes
        episodes_result = await db_session.execute(
            text(
                "SELECT id, episode_summary, emotional_peak, created_at "
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
                "emotional_peak": row[2]
                if isinstance(row[2], dict)
                else {"valence": float(row[2] or 0.0)},
                "created_at": row[3].isoformat() if row[3] else None,
            }
            for row in episodes_result.fetchall()
        ]
    except Exception as e:
        logger.debug("episodic_memories_query_failed", error=str(e))

    try:
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
    except Exception as e:
        logger.debug("fact_nodes_query_failed", error=str(e))

    return {
        "user_id": str(user_id),
        "character_id": character_id,
        "episodes": episodes,
        "facts": facts,
    }


@memory_router.get("/l4")
async def get_l4_identity(
    user_id: UUID = Query(..., description="User UUID"),
    character_id: str = Query("rin", description="Character ID"),
    db_session: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Get L4 identity memories (她记得的我)."""
    if str(current_user.user_id) != str(user_id):
        raise HTTPException(403, "Cannot read another user's identity")
    """Get L4 identity memories (她记得的我)."""
    memories = []
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
    except Exception as e:
        logger.debug("identity_memories_query_failed", error=str(e))

    return {
        "user_id": str(user_id),
        "character_id": character_id,
        "count": len(memories),
        "memories": memories,
    }


@memory_router.post("/forget")
async def forget_memory(
    user_id: UUID = Query(..., description="User UUID"),
    memory_id: str = Query(..., description="Memory ID to forget (soft delete)"),
    db_session: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Soft-delete a memory by setting do_not_recall=true (M-1: no physical deletion)."""
    if str(current_user.user_id) != str(user_id):
        raise HTTPException(403, "Cannot delete another user's memory")
    """Soft-delete a memory by setting do_not_recall=true (M-1: no physical deletion)."""
    try:
        result = await db_session.execute(
            text(
                "UPDATE episodic_memories SET do_not_recall = true "
                "WHERE id = :memory_id AND user_id = :user_id"
            ),
            {"memory_id": memory_id, "user_id": str(user_id)},
        )
        await db_session.commit()

        if result.rowcount > 0:  # type: ignore[attr-defined]
            logger.info("memory_forgotten", memory_id=memory_id, user_id=str(user_id))
            return {
                "status": "ok",
                "memory_id": memory_id,
                "message": "已软删除 (do_not_recall=true)",
            }
        return {"status": "not_found", "memory_id": memory_id, "message": "未找到该记忆"}
    except Exception as e:
        logger.error("forget_memory_failed", error=str(e))
        return {"status": "error", "error": str(e)}


dev_router = APIRouter(prefix="/api/dev", tags=["dev-tools"])


@dev_router.post("/jump_phase")
async def jump_phase(
    user_id: UUID = Query(..., description="User UUID"),
    character_id: str = Query("rin", description="Character ID"),
    phase: int = Query(..., description="Target phase (1-7)"),
    dev: bool = Query(False, description="Dev mode flag from CLI"),
    db_session: AsyncSession = Depends(get_db),
):
    """Jump to a specific relationship phase (dev mode only)."""
    import os

    server_dev = os.getenv("HEART_DEV_MODE", "").lower() == "true"
    if not server_dev and not dev:
        return {"error": "Dev mode not enabled. Set HEART_DEV_MODE=true or pass dev=true"}

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
                "INSERT INTO relationship_states (user_id, character_id, current_stage, trust_score, "
                "attachment_strength, intimacy_level, total_interactions, first_meeting_at, updated_at, "
                "soul_modifiers) "
                "VALUES (:user_id, :character_id, :stage, 0.0, 0.0, 0.0, 0, NOW(), NOW(), '{}'::jsonb) "
                "ON CONFLICT (user_id, character_id) DO UPDATE SET current_stage = :stage, updated_at = NOW()"
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
        logger.error("jump_phase_failed", error=str(e))
        return {"error": str(e)}


@dev_router.post("/sleep")
async def dev_sleep(
    user_id: UUID = Query(..., description="User UUID"),
    character_id: str = Query("rin", description="Character ID"),
    hours: int = Query(24, description="Hours to fast-forward"),
    dev: bool = Query(False, description="Dev mode flag from CLI"),
    db_session: AsyncSession = Depends(get_db),
):
    """Fast-forward time by N hours (triggers decay + inner loop tick)."""
    import os

    server_dev = os.getenv("HEART_DEV_MODE", "").lower() == "true"
    if not server_dev and not dev:
        return {"error": "Dev mode not enabled. Set HEART_DEV_MODE=true or pass dev=true"}

    try:
        # Update last_activity_at to simulate time passing
        from datetime import datetime, timezone

        cutoff = datetime.now(timezone.utc) - __import__("datetime").timedelta(hours=hours)
        await db_session.execute(
            text(
                "UPDATE sessions SET last_activity_at = :cutoff "
                "WHERE user_id = :user_id AND character_id = :character_id"
            ),
            {"user_id": str(user_id), "character_id": character_id, "cutoff": cutoff},
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
        logger.error("dev_sleep_failed", error=str(e))
        return {"error": str(e)}


@dev_router.post("/coldwar")
async def dev_coldwar(
    user_id: UUID = Query(..., description="User UUID"),
    character_id: str = Query("rin", description="Character ID"),
    active: bool = Query(True, description="Activate or deactivate cold war"),
    dev: bool = Query(False, description="Dev mode flag from CLI"),
    db_session: AsyncSession = Depends(get_db),
):
    """Force cold war state on/off (dev mode only)."""
    import os

    server_dev = os.getenv("HEART_DEV_MODE", "").lower() == "true"
    if not server_dev and not dev:
        return {"error": "Dev mode not enabled. Set HEART_DEV_MODE=true or pass dev=true"}

    try:
        # Update relationship state using UPSERT
        target_stage = "cold_war" if active else "friend"
        await db_session.execute(
            text(
                "INSERT INTO relationship_states (user_id, character_id, current_stage, trust_score, "
                "attachment_strength, intimacy_level, total_interactions, first_meeting_at, updated_at, "
                "soul_modifiers) "
                "VALUES (:user_id, :character_id, :stage, 0.0, 0.0, 0.0, 0, NOW(), NOW(), '{}'::jsonb) "
                "ON CONFLICT (user_id, character_id) DO UPDATE SET current_stage = :stage, updated_at = NOW()"
            ),
            {"user_id": str(user_id), "character_id": character_id, "stage": target_stage},
        )
        await db_session.commit()

        return {
            "user_id": str(user_id),
            "character_id": character_id,
            "cold_war_active": active,
        }
    except Exception as e:
        logger.error("dev_coldwar_failed", error=str(e))
        return {"error": str(e)}
