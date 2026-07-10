"""Profile API routes — /api/profile/*"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.api.rate_limit import limiter
from heart.api.wiring import get_db
from heart.core.auth import TokenData, get_current_user

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/profile", tags=["profile"])


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=20)
    gender: Optional[str] = None
    birthdate: Optional[str] = None  # ISO date string YYYY-MM-DD
    timezone: Optional[str] = Field(None, max_length=64)  # IANA tz, e.g. "Asia/Shanghai"


@router.get("")
async def get_profile(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return current user profile."""
    result = await db.execute(
        text("""
            SELECT id, email, display_name, avatar_url, gender, birthdate,
                   age_verified_at, credits_balance, status
            FROM users WHERE id = :id
        """),
        {"id": uuid.UUID(current_user.user_id)},
    )
    user = result.mappings().first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "user": {
            "id": str(user["id"]),
            "email": user["email"],
            "display_name": user["display_name"],
            "avatar_url": user["avatar_url"],
            "gender": user["gender"],
            "birthdate": str(user["birthdate"]) if user["birthdate"] else None,
            "age_verified": user["age_verified_at"] is not None,
            "credits_balance": user["credits_balance"],
        }
    }


def _apply_birthdate(
    birthdate: str,
    updates: list,
    params: dict,
) -> Optional[bool]:
    """Validate birthdate, append SQL fragment, return age_verified flag or raise."""
    try:
        bd = date.fromisoformat(birthdate)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format, use YYYY-MM-DD") from None

    today = date.today()
    age_precise = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
    updates.append("birthdate = :birthdate")
    params["birthdate"] = bd

    if age_precise >= 18:
        updates.append("age_verified_at = NOW()")
        return True
    return False


@router.patch("")
async def update_profile(
    body: ProfileUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update profile fields. Server-side 18+ verification on birthdate."""
    uid = uuid.UUID(current_user.user_id)
    updates = []
    params: dict = {"uid": uid}

    if body.display_name is not None:
        name = body.display_name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Display name cannot be empty")
        updates.append("display_name = :display_name")
        params["display_name"] = name

    if body.gender is not None:
        if body.gender not in ("female", "male", "nonbinary", "undisclosed"):
            raise HTTPException(status_code=400, detail="Invalid gender value")
        updates.append("gender = :gender")
        params["gender"] = body.gender

    if body.timezone is not None:
        try:
            from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

            ZoneInfo(body.timezone)
        except (ZoneInfoNotFoundError, KeyError):
            raise HTTPException(status_code=400, detail="Invalid timezone") from None
        updates.append("timezone = :timezone")
        params["timezone"] = body.timezone

    age_verified = None
    if body.birthdate is not None:
        age_verified = _apply_birthdate(body.birthdate, updates, params)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    query = f"UPDATE users SET {', '.join(updates)} WHERE id = :uid RETURNING id"
    await db.execute(text(query), params)
    await db.commit()

    if age_verified is False:
        return {"age_verified": False, "message": "未满 18 周岁，无法使用本产品"}

    return {"ok": True, "age_verified": age_verified}


@router.post("/avatar")
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upload avatar image. Uses MinIO/S3 when configured, fallback to base64."""
    uid = uuid.UUID(current_user.user_id)

    # Validate file type
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=400, detail="Only jpg/png/webp allowed")

    # Read and validate size (max 5MB)
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")

    from heart.infra.storage import is_s3_configured
    from heart.infra.storage import upload_avatar as s3_upload_avatar

    if is_s3_configured():
        try:
            avatar_url = await s3_upload_avatar(str(uid), data, file.content_type)
        except Exception as exc:
            logger.warning("avatar_s3_upload_failed_fallback_to_data_url", error=str(exc))
            import base64

            b64 = base64.b64encode(data).decode()
            avatar_url = f"data:{file.content_type};base64,{b64}"
    else:
        import base64

        b64 = base64.b64encode(data).decode()
        avatar_url = f"data:{file.content_type};base64,{b64}"

    await db.execute(
        text("UPDATE users SET avatar_url = :url WHERE id = :uid"),
        {"url": avatar_url, "uid": uid},
    )
    await db.commit()

    return {"avatar_url": avatar_url}


@router.get("/avatar-file/{path:path}")
async def get_avatar_file(path: str) -> Response:
    """Proxy avatar file from S3/MinIO storage."""
    from heart.core.config import settings
    from heart.infra.storage import get_s3_object

    try:
        data, content_type = await get_s3_object(f"avatars/{path}")
        return Response(content=data, media_type=content_type)
    except Exception as exc:
        logger.warning("avatar_proxy_fetch_failed", path=path, error=str(exc))
        raise HTTPException(status_code=404, detail="Avatar not found") from exc
