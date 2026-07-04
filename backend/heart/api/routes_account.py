"""Account management routes — /api/account/*"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.core.auth import TokenData, get_current_user

from .wiring import get_db

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/account", tags=["account"])


@router.post("/clear-conversations")
async def clear_conversations(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Clear chat messages and L1 Redis cache for current user.

    Does NOT delete long-term memory (L2/L3/L4).
    """
    uid = uuid.UUID(current_user.user_id)

    # Clear chat_messages (if table exists — Module 1 creates it)
    try:
        await db.execute(
            text("DELETE FROM chat_messages WHERE user_id = :uid"),
            {"uid": uid},
        )
    except Exception:
        pass  # Table may not exist yet

    # Clear L1 Redis working memory
    try:
        import redis.asyncio as aioredis

        from heart.core.config import settings

        r = aioredis.from_url(settings.redis_url)
        # Clear L1 memory keys for this user
        pattern = f"memory:l1:{uid}:*"
        async for key in r.scan_iter(match=pattern, count=100):
            await r.delete(key)
        await r.close()
    except Exception as e:
        logger.warning("clear_redis_failed", error=str(e))

    await db.commit()
    logger.info("conversations_cleared", user_id=str(uid))
    return {"ok": True}


class DeleteAccountRequest(BaseModel):
    confirm: str  # Must be user's email or "DELETE"


@router.post("/delete")
async def delete_account(
    body: DeleteAccountRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Soft-delete user account with 30-day grace period.

    - Sets status=deleted, anonymizes email
    - Revokes all auth sessions
    - Creates deletion request for scheduled purge
    """
    uid = uuid.UUID(current_user.user_id)

    # Get user email for confirmation
    result = await db.execute(
        text("SELECT email, status FROM users WHERE id = :uid"),
        {"uid": uid},
    )
    user = result.mappings().first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user["status"] == "deleted":
        raise HTTPException(status_code=400, detail="Account already deleted")

    # Confirm must match email
    if body.confirm != user["email"]:
        raise HTTPException(status_code=400, detail="Confirmation does not match email")

    # Anonymize email + soft delete
    anon_email = f"deleted+{uuid.uuid4()}@invalid"
    await db.execute(
        text("""
            UPDATE users
            SET status = 'deleted', deleted_at = NOW(), email = :anon
            WHERE id = :uid
        """),
        {"anon": anon_email, "uid": uid},
    )

    # Revoke all sessions
    await db.execute(
        text(
            "UPDATE auth_sessions SET revoked_at = NOW() WHERE user_id = :uid AND revoked_at IS NULL"
        ),
        {"uid": uid},
    )

    # Create deletion request (30-day purge schedule)
    purge_after = datetime.now(timezone.utc) + timedelta(days=30)
    await db.execute(
        text("""
            INSERT INTO account_deletion_requests (id, user_id, purge_after, status)
            VALUES (:id, :uid, :purge, 'pending')
        """),
        {"id": uuid.uuid4(), "uid": uid, "purge": purge_after},
    )

    await db.commit()
    logger.info("account_deleted", user_id=str(uid))
    return {"ok": True, "message": "账号已注销，30 天后数据将被永久删除"}


@router.post("/export")
async def export_data(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Export user data as JSON (GDPR-style)."""
    uid = uuid.UUID(current_user.user_id)

    # Profile
    user_result = await db.execute(
        text("""
            SELECT id, email, display_name, avatar_url, gender, birthdate,
                   credits_balance, created_at
            FROM users WHERE id = :uid
        """),
        {"uid": uid},
    )
    user = user_result.mappings().first()

    # Credits ledger
    tx_result = await db.execute(
        text("""
            SELECT delta, type, ref_type, ref_id, balance_after, created_at
            FROM credit_transactions WHERE user_id = :uid
            ORDER BY created_at
        """),
        {"uid": uid},
    )
    transactions = [dict(r) for r in tx_result.mappings().all()]

    # Character settings
    settings_result = await db.execute(
        text(
            "SELECT character_id, voice_enabled FROM user_character_settings WHERE user_id = :uid"
        ),
        {"uid": uid},
    )
    char_settings = [dict(r) for r in settings_result.mappings().all()]

    # Chat messages
    chat_result = await db.execute(
        text("""
            SELECT character_id, role, content, modality, credits_charged, created_at
            FROM chat_messages WHERE user_id = :uid
            ORDER BY created_at
        """),
        {"uid": uid},
    )
    chat_messages = [dict(r) for r in chat_result.mappings().all()]

    return {
        "profile": dict(user) if user else None,
        "transactions": transactions,
        "character_settings": char_settings,
        "chat_messages": chat_messages,
    }
