"""Shared FastAPI dependencies for commercial auth/billing."""

from __future__ import annotations

import uuid

import structlog
from fastapi import Depends, HTTPException, status
from sqlalchemy import text

from heart.core.auth import TokenData, get_current_user

from .wiring import _get_engine

logger = structlog.get_logger(__name__)


async def require_age_verified(
    current_user: TokenData = Depends(get_current_user),
) -> TokenData:
    """FastAPI dependency: reject users who haven't passed 18+ verification.

    Chains after get_current_user. Loads age_verified_at from DB.
    If NULL → 403 age_verification_required.
    """
    from sqlalchemy.ext.asyncio import AsyncSession

    uid = uuid.UUID(current_user.user_id)
    async with AsyncSession(_get_engine(), expire_on_commit=False) as db:
        result = await db.execute(
            text("SELECT age_verified_at FROM users WHERE id = :uid"),
            {"uid": uid},
        )
        age_verified_at = result.scalar_one_or_none()

    if age_verified_at is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="age_verification_required",
        )

    return current_user
