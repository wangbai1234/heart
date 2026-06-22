"""API routes for Heart application — per runtime_specs/07_agent_orchestration.md §3.9 and §10"""

from __future__ import annotations

import uuid as _uuid_mod
from typing import Optional
from uuid import UUID as _UUID

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from heart.core.auth import Token, TokenData, auth_manager

from .wiring import get_db, get_orchestrator

logger = structlog.get_logger()

router = APIRouter(prefix="/api", tags=["api"])


class LoginRequest(BaseModel):
    user_id: str
    email: Optional[str] = None


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


async def get_current_user(authorization: Optional[str] = Header(None)) -> TokenData:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authenticated",
        )
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid authorization header",
        )
    token = parts[1]
    return auth_manager.verify_token(token)


@router.post("/auth/login", response_model=Token)
async def login(request: LoginRequest) -> Token:
    logger.info("user_login", user_id=request.user_id, email=request.email)
    token = auth_manager.create_access_token(
        user_id=request.user_id,
        email=request.email,
    )
    return token


@router.post("/auth/refresh", response_model=Token)
async def refresh_token(current_user: TokenData = Depends(get_current_user)) -> Token:
    new_token = auth_manager.create_access_token(
        user_id=current_user.user_id,
        email=current_user.email,
    )
    logger.info("token_refreshed", user_id=current_user.user_id)
    return new_token


@router.get("/auth/verify")
async def verify_token(current_user: TokenData = Depends(get_current_user)) -> dict:
    return {
        "user_id": current_user.user_id,
        "email": current_user.email,
        "exp": current_user.exp.isoformat() if current_user.exp else None,
        "valid": True,
    }


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


# ── /api/chat — orchestrator-backed hot path ─────────────────────────


def _last_user_message(messages: list[ChatMessage]) -> Optional[str]:
    """Extract the last user message from the message list."""
    for msg in reversed(messages):
        if msg.role == "user":
            return msg.content
    return None


def _coerce_uuid(uid: str) -> _UUID:
    """Parse a string to UUID, falling back to UUID5 if not a valid UUID."""
    try:
        return _UUID(uid)
    except ValueError:
        return _uuid_mod.uuid5(_uuid_mod.NAMESPACE_DNS, uid)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: TokenData = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
    orchestrator=Depends(get_orchestrator),
) -> ChatResponse:
    """Real chat endpoint — delegates to Orchestrator.

    Pipeline (in Orchestrator):
      1. SessionManager.get_or_create_session
      2. SafetyAgent.classify (PURPLE → care path)
      3. ComposerService.compose (fail-soft fallback)
      4. MemoryService.encode_fast + InnerStateService.tick (fire-and-forget)
    """
    last = _last_user_message(request.messages)
    if not last:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No user message found")

    user_uuid = _coerce_uuid(str(current_user.user_id))
    history = [{"role": m.role, "content": m.content} for m in request.messages[:-1]]
    trace_id = _uuid_mod.uuid4()

    from heart.ss07_orchestration.models import TurnRequest

    turn_req = TurnRequest(
        user_id=user_uuid,
        character_id=request.character_id,
        user_message=last,
        history=history,
        trace_id=trace_id,
    )
    turn_resp = await orchestrator.handle_turn(turn_req, db_session=db_session)
    return ChatResponse(
        response=turn_resp.response,
        character_id=turn_resp.character_id,
        message_id=str(turn_resp.trace_id),
    )


# ── Health / Debug ──────────────────────────────────────────────────


@router.get("/health/ready", tags=["health"])
async def readiness_check():
    return {"status": "ready", "components": {"api": "ok", "auth": "ok"}}


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
