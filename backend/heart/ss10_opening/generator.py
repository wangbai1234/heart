"""Opening Generator — generates first-encounter scene for a character.

Called once per user×character pair when the user first enters chat.
Produces a structured opening (scene + action + dialogue) persisted as
regular chat_messages rows.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional
from uuid import UUID

import structlog
from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from .prompt_builder import build_opening_prompt
from .splitter import OpeningBubble, split_opening

logger = structlog.get_logger(__name__)


async def generate_opening(
    *,
    user_id: UUID,
    character_id: str,
    db: AsyncSession,
    model_router: Any,
    soul_registry: Any,
) -> list[dict[str, Any]]:
    """Generate and persist opening scene messages.

    Returns a list of message dicts (same shape as getChatHistory items)
    or empty list on failure.
    """
    try:
        spec = soul_registry.get_soul(character_id)
    except Exception:
        logger.warning("opening_no_spec", character_id=character_id)
        return []

    display_name = _resolve_display_name(spec)
    persona = _resolve_persona(spec)
    backstory = _resolve_backstory(spec)
    tags = _resolve_tags(spec)
    greeting_style = _resolve_greeting_style(spec)

    messages = build_opening_prompt(
        display_name=display_name,
        persona=persona,
        backstory=backstory,
        tags=tags,
        greeting_style=greeting_style,
    )

    if model_router is None:
        logger.warning("opening_no_model_router")
        return []

    try:
        raw_text = await model_router.call_cheap(
            messages=messages,
            temperature=0.9,
            max_tokens=500,
            agent_name=f"Opening.{character_id}",
        )
    except Exception:
        logger.exception("opening_generation_failed", character_id=character_id)
        return []

    if not raw_text or not raw_text.strip():
        logger.warning("opening_empty_response", character_id=character_id)
        return []

    bubbles = split_opening(raw_text)
    if not bubbles:
        return []

    turn_id = uuid.uuid4()
    persisted = await _persist_opening(
        db=db,
        user_id=user_id,
        character_id=character_id,
        turn_id=turn_id,
        bubbles=bubbles,
    )

    logger.info(
        "opening_generated",
        character_id=character_id,
        bubble_count=len(persisted),
    )
    return persisted


async def _persist_opening(
    *,
    db: AsyncSession,
    user_id: UUID,
    character_id: str,
    turn_id: uuid.UUID,
    bubbles: list[OpeningBubble],
) -> list[dict[str, Any]]:
    """Write opening bubbles to chat_messages and return API-shaped dicts."""
    results: list[dict[str, Any]] = []

    for bubble in bubbles:
        msg_id = uuid.uuid4()
        await db.execute(
            sql_text("""
                INSERT INTO chat_messages
                    (id, user_id, character_id, turn_id, role, content,
                     modality, kind, credits_charged, is_opening)
                VALUES
                    (:id, :uid, :cid, :tid, 'assistant', :content,
                     'text', :kind, 0, TRUE)
            """),
            {
                "id": msg_id,
                "uid": user_id,
                "cid": character_id,
                "tid": turn_id,
                "content": bubble.content,
                "kind": bubble.kind,
            },
        )
        results.append(
            {
                "id": str(msg_id),
                "role": "assistant",
                "content": bubble.content,
                "modality": "text",
                "audio_url": None,
                "audio_duration_ms": None,
                "credits_charged": 0,
                "turn_id": str(turn_id),
                "created_at": None,
                "kind": bubble.kind,
            }
        )

    # Record in opening_history for idempotency (survives chat clear)
    try:
        await db.execute(
            sql_text("""
                INSERT INTO opening_history (user_id, character_id)
                VALUES (:uid, :cid)
                ON CONFLICT DO NOTHING
            """),
            {"uid": user_id, "cid": character_id},
        )
    except Exception:
        pass  # Table may not exist yet pre-migration; messages still persisted

    await db.commit()

    # Backfill created_at from DB (NOW() default)
    if results:
        row = await db.execute(
            sql_text("""
                SELECT created_at FROM chat_messages
                WHERE turn_id = :tid AND user_id = :uid
                ORDER BY created_at ASC LIMIT 1
            """),
            {"tid": turn_id, "uid": user_id},
        )
        ts_row = row.scalar()
        if ts_row:
            ts_iso = ts_row.isoformat()
            for r in results:
                r["created_at"] = ts_iso

    return results


def _resolve_display_name(spec: Any) -> str:
    dn = getattr(spec, "display_name", None)
    if dn:
        return getattr(dn, "zh", None) or getattr(dn, "en", None) or str(dn)
    return getattr(spec, "character_id", "角色")


def _resolve_persona(spec: Any) -> str:
    anchor = getattr(spec, "identity_anchor", None)
    if anchor:
        archetype = getattr(anchor, "archetype", None)
        if archetype:
            return str(archetype)[:500]
    draft = getattr(spec, "_draft", None)
    if draft and hasattr(draft, "persona"):
        return str(draft.persona)[:500]
    return ""


def _resolve_backstory(spec: Any) -> Optional[str]:
    draft = getattr(spec, "_draft", None)
    if draft and hasattr(draft, "backstory"):
        return draft.backstory
    return None


def _resolve_tags(spec: Any) -> list[str]:
    draft = getattr(spec, "_draft", None)
    if draft and hasattr(draft, "tags"):
        return list(draft.tags) if draft.tags else []
    return []


def _resolve_greeting_style(spec: Any) -> str:
    draft = getattr(spec, "_draft", None)
    if draft and hasattr(draft, "greeting_style"):
        gs = draft.greeting_style
        return gs.value if hasattr(gs, "value") else str(gs)
    # Infer from spec's relational defaults
    rel = getattr(spec, "relational_template", None)
    if rel:
        distance = getattr(rel, "default_distance", "")
        if "guarded" in str(distance):
            return "cool"
        if "intense" in str(distance):
            return "intense"
    return "warm"
