"""OTP-based email login + real user system.

Routes for /api/auth:
  - POST /otp/request: send OTP code to email
  - POST /otp/verify: verify OTP code, return JWT tokens
  - POST /refresh: refresh access token
  - POST /logout: revoke refresh token
  - GET /me: return current user info
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.core.auth import TokenData, auth_manager, get_current_user
from heart.core.config import settings
from heart.infra.email import get_email_sender
from heart.infra.email.sender import (
    OTP_SUBJECT,
    render_otp_email,
)

from .rate_limit import limiter
from .wiring import get_db

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ── OTP helpers ─────────────────────────────────────────────────────


def _hash_code(code: str) -> str:
    """Hash OTP code with pepper using sha256."""
    pepper = settings.otp_pepper
    return hashlib.sha256(f"{code}{pepper}".encode()).hexdigest()


def _constant_time_compare(a: str, b: str) -> bool:
    """Constant-time string comparison."""
    return hmac.compare_digest(a.encode(), b.encode())


def _generate_code(length: int = 6) -> str:
    """Generate a numeric OTP code."""
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


# ── Request / Response models ───────────────────────────────────────


class OtpRequest(BaseModel):
    email: EmailStr


class OtpVerify(BaseModel):
    email: EmailStr
    code: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    gender: Optional[str] = None
    birthdate: Optional[str] = None
    age_verified: bool = False
    credits_balance: float = 0.0


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
    needs_profile: bool


# ── Rate limit key helpers (per-email, Redis-based) ─────────────────


async def _check_email_rate_limit(redis_client, email: str) -> bool:
    """Check if email has exceeded hourly OTP request limit.

    Returns True if allowed, False if exceeded.
    """
    key = f"otp:req:{email}"
    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, 3600)
    return count <= settings.otp_max_per_hour


async def _check_cooldown(redis_client, email: str) -> int:
    """Check cooldown between OTP requests.

    Returns remaining cooldown seconds (0 if ready).
    """
    key = f"otp:cooldown:{email}"
    ttl = await redis_client.ttl(key)
    return max(0, ttl)


async def _set_cooldown(redis_client, email: str) -> None:
    """Set cooldown for email."""
    key = f"otp:cooldown:{email}"
    await redis_client.setex(key, settings.otp_resend_cooldown_seconds, "1")


# ── Routes ──────────────────────────────────────────────────────────


@router.post("/otp/request")
@limiter.limit("5/minute")
async def request_otp(
    request: Request,
    body: OtpRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Send OTP code to email.

    Anti-abuse: per-IP rate limit (5/min), per-email hourly limit (5/hr),
    cooldown (60s). Returns same structure regardless of email existence.
    """
    import redis.asyncio as aioredis

    email = body.email.strip().lower()

    # Redis checks
    r = aioredis.from_url(settings.redis_url)
    try:
        # Cooldown
        remaining = await _check_cooldown(r, email)
        if remaining > 0:
            return {"sent": True, "cooldown": remaining, "expires_in": settings.otp_ttl_seconds}

        # Hourly limit
        allowed = await _check_email_rate_limit(r, email)
        if not allowed:
            logger.warning("otp_rate_limited", email=email[:3] + "***")
            return {
                "sent": True,
                "cooldown": settings.otp_resend_cooldown_seconds,
                "expires_in": settings.otp_ttl_seconds,
            }

        # Set cooldown
        await _set_cooldown(r, email)
    finally:
        await r.close()

    # Generate and store OTP
    code = _generate_code(6)
    code_hash = _hash_code(code)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.otp_ttl_seconds)
    request_ip = request.client.host if request.client else None

    await db.execute(
        text("""
            INSERT INTO email_otp_codes (id, email, code_hash, purpose, expires_at, request_ip)
            VALUES (:id, :email, :code_hash, 'login', :expires_at, :request_ip)
        """),
        {
            "id": uuid.uuid4(),
            "email": email,
            "code_hash": code_hash,
            "expires_at": expires_at,
            "request_ip": request_ip,
        },
    )
    await db.commit()

    # Send email (fire-and-log, don't leak existence)
    try:
        sender = get_email_sender()
        subject = OTP_SUBJECT.format(code=code)
        plain, html = render_otp_email(code)
        await sender.send(to=email, subject=subject, body=plain, html=html)
    except Exception as e:
        logger.error("otp_email_send_failed", email=email[:3] + "***", error=str(e))

    logger.info("otp_requested", email=email[:3] + "***")
    return {
        "sent": True,
        "cooldown": settings.otp_resend_cooldown_seconds,
        "expires_in": settings.otp_ttl_seconds,
    }


@router.post("/otp/verify")
@limiter.limit("10/minute")
async def verify_otp(
    request: Request,
    body: OtpVerify,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Verify OTP code and return JWT tokens.

    On success: upsert user, grant signup credits (idempotent),
    issue access + refresh tokens.
    """
    email = body.email.strip().lower()
    code = body.code.strip()

    # Get latest unconsumed OTP for this email
    result = await db.execute(
        text("""
            SELECT id, code_hash, expires_at, consumed_at, attempts
            FROM email_otp_codes
            WHERE email = :email AND purpose = 'login'
            ORDER BY created_at DESC
            LIMIT 1
        """),
        {"email": email},
    )
    row = result.mappings().first()

    # Always do a dummy compare to prevent timing attacks
    dummy_hash = _hash_code("000000")
    if row is None:
        _constant_time_compare(dummy_hash, dummy_hash)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired code"
        )

    if row["consumed_at"] is not None:
        _constant_time_compare(dummy_hash, dummy_hash)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired code"
        )

    if row["expires_at"] < datetime.now(timezone.utc):
        _constant_time_compare(dummy_hash, dummy_hash)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Code expired")

    if row["attempts"] >= settings.otp_max_attempts:
        _constant_time_compare(dummy_hash, dummy_hash)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Too many attempts, request a new code"
        )

    # Increment attempts
    await db.execute(
        text("UPDATE email_otp_codes SET attempts = attempts + 1 WHERE id = :id"),
        {"id": row["id"]},
    )

    # Constant-time compare
    code_hash = _hash_code(code)
    if not _constant_time_compare(code_hash, row["code_hash"]):
        await db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid code")

    # Mark consumed
    await db.execute(
        text("UPDATE email_otp_codes SET consumed_at = NOW() WHERE id = :id"),
        {"id": row["id"]},
    )

    # Upsert user
    user_result = await db.execute(
        text("""
            SELECT id, email, display_name, avatar_url, gender, birthdate,
                   age_verified_at, credits_balance, status
            FROM users WHERE email = :email
        """),
        {"email": email},
    )
    user_row = user_result.mappings().first()

    is_new_user = user_row is None
    if is_new_user:
        user_id = uuid.uuid4()
        await db.execute(
            text("""
                INSERT INTO users (id, email, credits_balance, status)
                VALUES (:id, :email, :credits, 'active')
                ON CONFLICT (email) DO NOTHING
            """),
            {"id": user_id, "email": email, "credits": settings.signup_grant_credits},
        )
        # Re-query in case of concurrent insert
        user_result = await db.execute(
            text("""
                SELECT id, email, display_name, avatar_url, gender, birthdate,
                       age_verified_at, credits_balance, status
                FROM users WHERE email = :email
            """),
            {"email": email},
        )
        user_row = user_result.mappings().first()
        if user_row is None:
            raise HTTPException(status_code=500, detail="User creation failed")
        user_id = user_row["id"]
        # Idempotent signup grant
        await db.execute(
            text("""
                INSERT INTO credit_transactions (id, user_id, delta, balance_after, type, idempotency_key, created_at)
                VALUES (:id, :uid, :delta, :balance, 'grant', :idem_key, NOW())
                ON CONFLICT (idempotency_key) DO NOTHING
            """),
            {
                "id": uuid.uuid4(),
                "uid": user_id,
                "delta": settings.signup_grant_credits,
                "balance": settings.signup_grant_credits,
                "idem_key": f"signup_grant:{user_id}",
            },
        )
        # Re-fetch user
        user_result = await db.execute(
            text("""
                SELECT id, email, display_name, avatar_url, gender, birthdate,
                       age_verified_at, credits_balance, status
                FROM users WHERE id = :id
            """),
            {"id": user_id},
        )
        user_row = user_result.mappings().first()
    else:
        user_id = user_row["id"]

    # Update last_login_at
    await db.execute(
        text("UPDATE users SET last_login_at = NOW() WHERE id = :id"),
        {"id": user_id},
    )

    await db.commit()

    # Generate tokens
    access_token = auth_manager.create_access_token(user_id=str(user_id), email=email)
    refresh_token_raw = secrets.token_hex(32)
    refresh_hash = hashlib.sha256(refresh_token_raw.encode()).hexdigest()

    await db.execute(
        text("""
            INSERT INTO auth_sessions (id, user_id, refresh_token_hash, expires_at, user_agent, ip)
            VALUES (:id, :uid, :hash, :expires, :ua, :ip)
        """),
        {
            "id": uuid.uuid4(),
            "uid": user_id,
            "hash": refresh_hash,
            "expires": datetime.now(timezone.utc)
            + timedelta(days=settings.refresh_token_expire_days),
            "ua": request.headers.get("user-agent"),
            "ip": request.client.host if request.client else None,
        },
    )
    await db.commit()

    needs_profile = user_row["birthdate"] is None or user_row["age_verified_at"] is None

    logger.info("otp_verified", user_id=str(user_id), is_new=is_new_user)

    return TokenResponse(
        access_token=access_token.access_token,
        refresh_token=refresh_token_raw,
        expires_in=access_token.expires_in,
        user=UserResponse(
            id=str(user_row["id"]),
            email=user_row["email"],
            display_name=user_row["display_name"],
            avatar_url=user_row["avatar_url"],
            gender=user_row["gender"],
            birthdate=str(user_row["birthdate"]) if user_row["birthdate"] else None,
            age_verified=user_row["age_verified_at"] is not None,
            credits_balance=user_row["credits_balance"] / 100,
        ),
        needs_profile=needs_profile,
    )


@router.post("/refresh")
@limiter.limit("30/minute")
async def refresh(
    request: Request,
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Refresh access token using refresh token.

    Rotates refresh token (old one revoked, new one issued).
    """
    refresh_hash = hashlib.sha256(body.refresh_token.encode()).hexdigest()

    result = await db.execute(
        text("""
            SELECT id, user_id, expires_at, revoked_at
            FROM auth_sessions
            WHERE refresh_token_hash = :hash
        """),
        {"hash": refresh_hash},
    )
    session = result.mappings().first()

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    if session["revoked_at"] is not None:
        # Token reuse detection — revoke all sessions for this user
        await db.execute(
            text(
                "UPDATE auth_sessions SET revoked_at = NOW() WHERE user_id = :uid AND revoked_at IS NULL"
            ),
            {"uid": session["user_id"]},
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked"
        )

    if session["expires_at"] < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired"
        )

    # Get user
    user_result = await db.execute(
        text("SELECT id, email FROM users WHERE id = :id AND status = 'active'"),
        {"id": session["user_id"]},
    )
    user = user_result.mappings().first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # Revoke old session
    await db.execute(
        text("UPDATE auth_sessions SET revoked_at = NOW() WHERE id = :id"),
        {"id": session["id"]},
    )

    # Issue new tokens
    access_token = auth_manager.create_access_token(user_id=str(user["id"]), email=user["email"])
    new_refresh_raw = secrets.token_hex(32)
    new_refresh_hash = hashlib.sha256(new_refresh_raw.encode()).hexdigest()

    await db.execute(
        text("""
            INSERT INTO auth_sessions (id, user_id, refresh_token_hash, expires_at)
            VALUES (:id, :uid, :hash, :expires)
        """),
        {
            "id": uuid.uuid4(),
            "uid": user["id"],
            "hash": new_refresh_hash,
            "expires": datetime.now(timezone.utc)
            + timedelta(days=settings.refresh_token_expire_days),
        },
    )
    await db.commit()

    return {
        "access_token": access_token.access_token,
        "refresh_token": new_refresh_raw,
        "expires_in": access_token.expires_in,
    }


@router.post("/logout")
@limiter.limit("30/minute")
async def logout(
    request: Request,
    body: LogoutRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Logout: revoke current refresh token."""
    if body.refresh_token:
        refresh_hash = hashlib.sha256(body.refresh_token.encode()).hexdigest()
        await db.execute(
            text("""
                UPDATE auth_sessions SET revoked_at = NOW()
                WHERE refresh_token_hash = :hash AND user_id = :uid
            """),
            {"hash": refresh_hash, "uid": uuid.UUID(current_user.user_id)},
        )
        await db.commit()

    return {"ok": True}


@router.get("/me")
@limiter.limit("60/minute")
async def get_me(
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return current user info."""
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return {
        "user": {
            "id": str(user["id"]),
            "email": user["email"],
            "display_name": user["display_name"],
            "avatar_url": user["avatar_url"],
            "gender": user["gender"],
            "birthdate": str(user["birthdate"]) if user["birthdate"] else None,
            "age_verified": user["age_verified_at"] is not None,
            "credits_balance": user["credits_balance"] / 100,
        }
    }
