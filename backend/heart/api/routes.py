"""API routes for Heart application — per runtime_specs/07_agent_orchestration.md §3.9 and §10"""

from __future__ import annotations

import uuid as _uuid_mod
from typing import Optional
from uuid import UUID as _UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from heart.api.rate_limit import limiter
from heart.core.auth import Token, TokenData, auth_manager, get_current_user

from .deps import require_age_verified
from .wiring import get_db, get_orchestrator

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

dev_auth_router = APIRouter(prefix="/auth", tags=["auth-dev"])


class LoginRequest(BaseModel):
    user_id: str
    email: Optional[str] = None


@dev_auth_router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(request: Request, login_req: LoginRequest) -> Token:
    """DEV-ONLY stub login: accepts any user_id, issues JWT immediately."""
    logger.warning("dev_login_used", user_id=login_req.user_id)
    token = auth_manager.create_access_token(
        user_id=login_req.user_id,
        email=login_req.email,
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
@limiter.limit("30/minute")
async def chat(
    request: Request,
    chat_req: ChatRequest,
    current_user: TokenData = Depends(require_age_verified),
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
    last = _last_user_message(chat_req.messages)
    if not last:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No user message found")

    user_uuid = _coerce_uuid(str(current_user.user_id))
    history = [{"role": m.role, "content": m.content} for m in chat_req.messages[:-1]]
    trace_id = _uuid_mod.uuid4()

    from heart.ss07_orchestration.models import TurnRequest

    turn_req = TurnRequest(
        user_id=user_uuid,
        character_id=chat_req.character_id,
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
