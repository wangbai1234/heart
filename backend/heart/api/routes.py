"""API routes for Heart application — per runtime_specs/07_agent_orchestration.md §3.9 and §10"""

from __future__ import annotations

import uuid as _uuid_mod
from typing import Optional
from uuid import UUID as _UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.api.rate_limit import limiter
from heart.core.auth import Token, TokenData, auth_manager, get_current_user
from heart.core.config import settings

from .wiring import get_db

logger = structlog.get_logger()

router = APIRouter(prefix="/api", tags=["api"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    character_id: str = "rin"


class ChatResponse(BaseModel):
    response: str
    character_id: str
    message_id: str


# ── Legacy stub login — DEV MODE ONLY (see main.py) ────────────────

dev_auth_router = APIRouter(prefix="/api/auth", tags=["auth-dev"])


class LoginRequest(BaseModel):
    user_id: str
    email: Optional[str] = None


@dev_auth_router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(
    request: Request,
    login_req: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """DEV-ONLY stub login: ensure a matching user row exists, then issue JWT."""
    logger.warning("dev_login_used", user_id=login_req.user_id)
    email = (login_req.email or f"{login_req.user_id}@dev.local").strip().lower()
    uid = _UUID(login_req.user_id)

    await db.execute(
        text(
            """
            INSERT INTO users (id, email, credits_balance, status, last_login_at)
            VALUES (:id, :email, :credits, 'active', NOW())
            ON CONFLICT (id) DO UPDATE
            SET email = EXCLUDED.email,
                status = 'active',
                last_login_at = NOW()
            """
        ),
        {
            "id": uid,
            "email": email,
            "credits": settings.signup_grant_credits,
        },
    )
    await db.commit()

    token = auth_manager.create_access_token(
        user_id=login_req.user_id,
        email=email,
    )
    return token


@dev_auth_router.post("/refresh", response_model=Token)
async def refresh_token(current_user: TokenData = Depends(get_current_user)) -> Token:
    """DEV-ONLY stub refresh."""
    new_token = auth_manager.create_access_token(
        user_id=current_user.user_id,
        email=current_user.email,
    )
    return new_token


@router.post("/chat/echo", response_model=ChatResponse)
async def echo_chat(
    request: ChatRequest,
    current_user: TokenData = Depends(get_current_user),
) -> ChatResponse:
    logger.info(
        "echo_chat_request",
        user_id=current_user.user_id,
        character_id=request.character_id,
        message_count=len(request.messages),
    )
    last_user_message = None
    for msg in reversed(request.messages):
        if msg.role == "user":
            last_user_message = msg.content
            break
    if not last_user_message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No user message found in request",
        )
    message_id = str(_uuid_mod.uuid4())
    response_text = f"[Echo from {request.character_id}] You said: {last_user_message}"
    return ChatResponse(
        response=response_text,
        character_id=request.character_id,
        message_id=message_id,
    )


# ── Health / Debug ──────────────────────────────────────────────────

# Debug routes — only mounted when HEART_DEV_MODE=true (see main.py)
dev_router = APIRouter(tags=["debug"])


@dev_router.get("/records")
async def get_profile_records():
    """Return collected turn profile records (debug only)."""
    from heart.observability.turn_profiler import get_collected_profiles

    records = get_collected_profiles()
    return {"count": len(records), "records": records}


@dev_router.post("/reset")
async def reset_profile_records():
    """Reset collected turn profile records (debug only)."""
    from heart.observability.turn_profiler import reset_collected_profiles

    reset_collected_profiles()
    return {"status": "reset"}
