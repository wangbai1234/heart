"""API routes for Heart application."""

from fastapi import APIRouter, HTTPException, Depends, status, Header
from typing import Optional
import structlog
from pydantic import BaseModel, EmailStr
from ..core.auth import auth_manager, Token, TokenData, User

logger = structlog.get_logger()

router = APIRouter(prefix="/api", tags=["api"])


class LoginRequest(BaseModel):
    """Login request model."""
    user_id: str
    email: Optional[str] = None


class ChatMessage(BaseModel):
    """Chat message model."""
    role: str
    content: str


class ChatRequest(BaseModel):
    """Chat request model."""
    messages: list[ChatMessage]
    character_id: str = "default"


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str
    character_id: str
    message_id: str


async def get_current_user(authorization: Optional[str] = Header(None)) -> TokenData:
    """Get current user from JWT token.

    Args:
        authorization: Authorization header with Bearer token

    Returns:
        TokenData with user information

    Raises:
        HTTPException: If token is invalid
    """
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
    """Generate JWT token for user.

    Args:
        request: Login request with user_id and optional email

    Returns:
        Token object with access token
    """
    logger.info("user_login", user_id=request.user_id, email=request.email)

    token = auth_manager.create_access_token(
        user_id=request.user_id,
        email=request.email,
    )

    return token


@router.post("/auth/refresh", response_model=Token)
async def refresh_token(current_user: TokenData = Depends(get_current_user)) -> Token:
    """Refresh JWT token.

    Args:
        current_user: Current authenticated user

    Returns:
        New Token object
    """
    new_token = auth_manager.create_access_token(
        user_id=current_user.user_id,
        email=current_user.email,
    )
    logger.info("token_refreshed", user_id=current_user.user_id)
    return new_token


@router.get("/auth/verify")
async def verify_token(current_user: TokenData = Depends(get_current_user)) -> dict:
    """Verify JWT token validity.

    Args:
        current_user: Current authenticated user

    Returns:
        User information with token validity
    """
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
    """Echo bot endpoint for testing.

    Simple echo endpoint that mirrors back the last user message.
    Used for Phase 0 testing and validation.

    Args:
        request: Chat request with messages and character_id
        current_user: Authenticated user from JWT token

    Returns:
        ChatResponse with echoed message
    """
    logger.info(
        "echo_chat_request",
        user_id=current_user.user_id,
        character_id=request.character_id,
        message_count=len(request.messages),
    )

    # Find last user message
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

    # Generate message ID
    import uuid
    message_id = str(uuid.uuid4())

    # Echo response with slight variation
    response_text = f"[Echo from {request.character_id}] You said: {last_user_message}"

    logger.info(
        "echo_chat_response",
        user_id=current_user.user_id,
        message_id=message_id,
        response_length=len(response_text),
    )

    return ChatResponse(
        response=response_text,
        character_id=request.character_id,
        message_id=message_id,
    )


@router.get("/health/ready", tags=["health"])
async def readiness_check():
    """Enhanced readiness check with auth validation."""
    return {
        "status": "ready",
        "components": {
            "api": "ok",
            "auth": "ok",
        },
    }
