"""Authenticated account notices with cross-device acknowledgement receipts."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.core.auth import TokenData, get_current_user

from .wiring import get_db

router = APIRouter(prefix="/api/notices", tags=["notices"])


@router.get("/active")
async def get_active_notice(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return the active notice unless this account has already acknowledged it."""
    uid = uuid.UUID(current_user.user_id)

    # Account-specific notices take precedence over global announcements.
    targeted = (
        (
            await db.execute(
                text(
                    """
                SELECT n.id, n.eyebrow, n.title, n.summary, n.content,
                       n.confirm_label, n.qr_image_url, n.starts_at, n.ends_at
                FROM user_notices n
                LEFT JOIN user_notice_receipts r
                  ON r.user_id = n.user_id AND r.notice_id = n.id
                WHERE n.user_id = :uid
                  AND n.starts_at <= NOW()
                  AND (n.ends_at IS NULL OR n.ends_at > NOW())
                  AND r.notice_id IS NULL
                ORDER BY n.starts_at DESC
                LIMIT 1
                """
                ),
                {"uid": uid},
            )
        )
        .mappings()
        .first()
    )
    if targeted is not None:
        return {
            "notice": {
                "id": targeted["id"],
                "eyebrow": targeted["eyebrow"],
                "title": targeted["title"],
                "summary": targeted["summary"],
                "content": targeted["content"],
                "confirm_label": targeted["confirm_label"],
                "qr_image_url": targeted["qr_image_url"],
                "starts_at": targeted["starts_at"].isoformat(),
                "ends_at": targeted["ends_at"].isoformat() if targeted["ends_at"] else None,
            }
        }

    # The global recovery popup has been retired. Keep this endpoint for
    # account-targeted one-off notices only.
    return {"notice": None}


@router.post("/{notice_id}/ack")
async def acknowledge_notice(
    notice_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Persist a notice acknowledgement idempotently for the current account."""
    uid = uuid.UUID(current_user.user_id)
    targeted = await db.execute(
        text("SELECT 1 FROM user_notices WHERE id = :notice_id AND user_id = :uid"),
        {"uid": uid, "notice_id": notice_id},
    )
    if targeted.first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="notice_not_found")

    await db.execute(
        text(
            "INSERT INTO user_notice_receipts (user_id, notice_id) "
            "VALUES (:uid, :notice_id) ON CONFLICT (user_id, notice_id) DO NOTHING"
        ),
        {"uid": uid, "notice_id": notice_id},
    )
    await db.commit()
    return {"ok": True}
