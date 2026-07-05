"""Character settings API routes — /api/characters/*"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.api.wiring import get_db
from heart.core.auth import TokenData, get_current_user

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/characters", tags=["characters"])


class VoiceSettingUpdate(BaseModel):
    voice_enabled: bool


@router.get("/{character_id}/settings")
async def get_character_settings(
    character_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get per-character settings (voice toggle)."""
    uid = uuid.UUID(current_user.user_id)
    result = await db.execute(
        text("""
            SELECT voice_enabled FROM user_character_settings
            WHERE user_id = :uid AND character_id = :cid
        """),
        {"uid": uid, "cid": character_id},
    )
    row = result.scalar_one_or_none()
    return {"voice_enabled": row if row is not None else False}


@router.patch("/{character_id}/settings")
async def update_character_settings(
    character_id: str,
    body: VoiceSettingUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update per-character voice toggle (upsert)."""
    uid = uuid.UUID(current_user.user_id)
    await db.execute(
        text("""
            INSERT INTO user_character_settings (user_id, character_id, voice_enabled, updated_at)
            VALUES (:uid, :cid, :ve, NOW())
            ON CONFLICT (user_id, character_id)
            DO UPDATE SET voice_enabled = :ve, updated_at = NOW()
        """),
        {"uid": uid, "cid": character_id, "ve": body.voice_enabled},
    )
    await db.commit()
    logger.info(
        "character_setting_updated",
        user_id=str(uid),
        character_id=character_id,
        voice_enabled=body.voice_enabled,
    )
    return {"voice_enabled": body.voice_enabled}


@router.post("/{character_id}/clear-conversations")
async def clear_character_conversations(
    character_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Clear persisted chat messages for one character only."""
    uid = uuid.UUID(current_user.user_id)

    try:
        await db.execute(
            text(
                """
                DELETE FROM chat_messages
                WHERE user_id = :uid AND character_id = :cid
                """
            ),
            {"uid": uid, "cid": character_id},
        )
    except Exception as exc:
        logger.warning(
            "character_conversations_clear_failed",
            user_id=str(uid),
            character_id=character_id,
            error=str(exc),
        )
        raise HTTPException(status_code=500, detail="清空聊天记录失败") from exc

    await db.commit()
    logger.info(
        "character_conversations_cleared",
        user_id=str(uid),
        character_id=character_id,
    )
    return {"ok": True}
