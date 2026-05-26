"""API routes for Heart application — per runtime_specs/07_agent_orchestration.md §3.9 and §10"""

from fastapi import APIRouter, HTTPException, Depends, status, Header
from typing import Optional, Any
import structlog
from pydantic import BaseModel
from ..core.auth import auth_manager, Token, TokenData
from ..core.config import settings

logger = structlog.get_logger()

router = APIRouter(prefix="/api", tags=["api"])


class LoginRequest(BaseModel):
    def __init__(self, **data):
        super().__init__(**data)
    user_id: str
    email: Optional[str] = None


class ChatMessage(BaseModel):
    def __init__(self, **data):
        super().__init__(**data)
    role: str
    content: str


class ChatRequest(BaseModel):
    def __init__(self, **data):
        super().__init__(**data)
    messages: list[ChatMessage]
    character_id: str = "default"


class ChatResponse(BaseModel):
    def __init__(self, **data):
        super().__init__(**data)
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
    import uuid
    message_id = str(uuid.uuid4())
    response_text = f"[Echo from {request.character_id}] You said: {last_user_message}"
    return ChatResponse(
        response=response_text,
        character_id=request.character_id,
        message_id=message_id,
    )


# ── Lazy singletons (SoulRegistry, ComposerService) ───────────────

_soul_registry: Optional[Any] = None
_composer_service: Optional[Any] = None


def _get_soul_registry():
    global _soul_registry
    if _soul_registry is not None:
        return _soul_registry
    from heart.ss01_soul.registry import SoulRegistry
    _soul_registry = SoulRegistry()
    try:
        _soul_registry.load_all()
        logger.info(
            "soul_registry_loaded",
            characters=list(_soul_registry._registry.keys()),
        )
    except Exception as e:
        logger.warning("soul_registry_load_failed", error=str(e))
    return _soul_registry


def _get_composer_service():
    global _composer_service
    if _composer_service is not None:
        return _composer_service

    registry = _get_soul_registry()

    # Try to create ModelRouter if DEEPSEEK_API_KEY is set
    model_router = None
    if settings.deepseek_api_key:
        try:
            from heart.infra.llm import LLMProviderConfig, DeepSeekConfig, ModelRouter
            llm_config = LLMProviderConfig(
                deepseek=DeepSeekConfig(
                    api_key=settings.deepseek_api_key,
                    base_url=settings.deepseek_base_url,
                ),
            )
            model_router = ModelRouter(llm_config)
            logger.info("model_router_initialized_for_chat")
        except Exception as e:
            logger.warning("model_router_init_failed", error=str(e))
    else:
        logger.warning(
            "no_llm_api_key",
            hint="Set DEEPSEEK_API_KEY in .env to enable real LLM responses",
        )

    from heart.ss05_composer.service import ComposerService
    _composer_service = ComposerService(
        soul_registry=registry,
        model_router=model_router,
    )
    logger.info("composer_service_initialized", has_llm=model_router is not None)
    return _composer_service


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: TokenData = Depends(get_current_user),
) -> ChatResponse:
    """Real chat endpoint — generates a character-driven response via LLM.

    Uses ComposerService with Soul Spec context (no DB required).
    Falls back to a character-aware template if LLM is not configured.
    """
    import uuid
    import time as _time

    message_id = str(uuid.uuid4())

    last_user_message = None
    for msg in reversed(request.messages):
        if msg.role == "user":
            last_user_message = msg.content
            break
    if not last_user_message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No user message found",
        )

    history = [{"role": msg.role, "content": msg.content} for msg in request.messages[:-1]]

    composer = _get_composer_service()

    from uuid import UUID as _UUID
    from heart.ss05_composer.service import CompositionContext

    # Map user_id string to deterministic UUID (for non-UUID user IDs)
    _user_id_str = str(current_user.user_id) if hasattr(current_user, "user_id") else str(uuid.uuid4())
    try:
        _user_uuid = _UUID(_user_id_str)
    except ValueError:
        _user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, _user_id_str)

    ctx = CompositionContext(
        user_id=_user_uuid,
        character_id=request.character_id,
        turn_id=uuid.UUID(message_id),
        max_tokens=2000,
    )

    t0 = _time.monotonic()
    try:
        result = await composer.compose(
            ctx=ctx,
            user_message=last_user_message,
            conversation_history=history,
            temperature=0.7,
        )
        response_text = result.response
    except Exception as exc:
        logger.error("composer_failed", error=str(exc), exc_info=True)
        name_map = {"rin": "凛", "dorothy": "Dorothy"}
        display = name_map.get(request.character_id.lower(), request.character_id)
        response_text = f"[{display}] 我听到你说的了。能多说一些吗？"

    latency = int((_time.monotonic() - t0) * 1000)
    logger.info(
        "chat_response",
        character_id=request.character_id,
        message_id=message_id,
        latency_ms=latency,
        response_length=len(response_text),
    )

    return ChatResponse(
        response=response_text,
        character_id=request.character_id,
        message_id=message_id,
    )


@router.get("/health/ready", tags=["health"])
async def readiness_check():
    return {"status": "ready", "components": {"api": "ok", "auth": "ok"}}
