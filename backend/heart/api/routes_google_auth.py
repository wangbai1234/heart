"""Google OIDC code flow with PKCE, nonce and single-use browser-bound handoff."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlsplit

import httpx
import jwt
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.api.rate_limit import limiter
from heart.api.routes_auth import TokenResponse, UserResponse
from heart.api.wiring import get_db
from heart.core.auth import auth_manager
from heart.core.config import settings
from heart.i18n import initialize_preferences, resolve_locale

router = APIRouter(prefix="/api/auth/google", tags=["auth"])
_COOKIE = "yuoyuo_google_flow"


def enabled() -> bool:
    return bool(
        settings.international_mode and settings.google_client_id and settings.google_client_secret
    )


def _require_config() -> None:
    if not enabled():
        raise HTTPException(503, "google_not_configured")
    for value in (settings.google_redirect_uri, settings.google_frontend_callback):
        url = urlsplit(value)
        if url.scheme != "https" and not (
            url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1"}
        ):
            raise HTTPException(503, "invalid_google_configuration")


@router.get("/config")
async def google_config() -> dict:
    return {"enabled": enabled()}


@router.get("/start")
@limiter.limit("10/minute")
async def google_start(request: Request) -> RedirectResponse:
    _require_config()
    state, nonce, verifier, browser = (secrets.token_urlsafe(32) for _ in range(4))
    flow = {
        "nonce": nonce,
        "verifier": verifier,
        "browser": browser,
        "locale": resolve_locale(request.headers.get("accept-language", "en")),
    }
    async with aioredis.from_url(settings.redis_url) as redis:
        await redis.setex(f"google:state:{state}", 600, json.dumps(flow))
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    )
    response = RedirectResponse(
        "https://accounts.google.com/o/oauth2/v2/auth?"
        + urlencode(
            {
                "client_id": settings.google_client_id,
                "redirect_uri": settings.google_redirect_uri,
                "response_type": "code",
                "scope": "openid email profile",
                "state": state,
                "nonce": nonce,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        ),
        status_code=303,
    )
    response.set_cookie(
        _COOKIE,
        browser,
        max_age=600,
        httponly=True,
        secure=settings.google_redirect_uri.startswith("https://"),
        samesite="lax",
        path="/api/auth/google",
    )
    response.headers["Cache-Control"] = "no-store"
    return response


async def _verify_google_token(encoded: str, nonce: str, client: httpx.AsyncClient) -> dict:
    """Keys come only from Google's fixed JWKS URL; never from token headers."""
    header = jwt.get_unverified_header(encoded)
    keys = await client.get("https://www.googleapis.com/oauth2/v3/certs")
    keys.raise_for_status()
    key = next((item for item in keys.json()["keys"] if item["kid"] == header.get("kid")), None)
    if key is None:
        raise ValueError("unknown_signing_key")
    claims = jwt.decode(
        encoded,
        jwt.PyJWK.from_dict(key).key,
        algorithms=["RS256"],
        audience=settings.google_client_id,
        options={"require": ["exp", "iat", "iss", "aud", "sub", "nonce", "email"]},
    )
    if claims["iss"] not in {"https://accounts.google.com", "accounts.google.com"}:
        raise ValueError("invalid_issuer")
    if (
        not hmac.compare_digest(str(claims["nonce"]), nonce)
        or claims.get("email_verified") is not True
    ):
        raise ValueError("unverified_identity")
    if claims.get("azp", settings.google_client_id) != settings.google_client_id:
        raise ValueError("invalid_authorized_party")
    return claims


@router.get("/callback")
@limiter.limit("15/minute")
async def google_callback(
    request: Request, state: str = "", code: str = "", error: str = ""
) -> RedirectResponse:
    _require_config()
    async with aioredis.from_url(settings.redis_url) as redis:
        raw = await redis.getdel(f"google:state:{state}") if state else None
        if raw is None:
            raise HTTPException(400, "invalid_google_state")
        flow = json.loads(raw)
        if not hmac.compare_digest(flow["browser"], request.cookies.get(_COOKIE, "")):
            raise HTTPException(400, "invalid_google_browser")
        if error or not code:
            return RedirectResponse(
                settings.google_frontend_callback + "#error=cancelled", status_code=303
            )
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "code": code,
                        "client_id": settings.google_client_id,
                        "client_secret": settings.google_client_secret,
                        "redirect_uri": settings.google_redirect_uri,
                        "grant_type": "authorization_code",
                        "code_verifier": flow["verifier"],
                    },
                )
                response.raise_for_status()
                claims = await _verify_google_token(
                    response.json()["id_token"], flow["nonce"], client
                )
        except (httpx.HTTPError, jwt.PyJWTError, ValueError, KeyError):
            raise HTTPException(400, "google_verification_failed") from None
        ticket = secrets.token_urlsafe(32)
        await redis.setex(
            f"google:ticket:{ticket}",
            90,
            json.dumps(
                {
                    "sub": claims["sub"],
                    "email": str(claims["email"]).lower(),
                    "authoritative_email": str(claims["email"]).lower().endswith("@gmail.com")
                    or bool(claims.get("hd")),
                    "browser": flow["browser"],
                    "locale": flow["locale"],
                }
            ),
        )
    result = RedirectResponse(
        settings.google_frontend_callback + "#ticket=" + ticket, status_code=303
    )
    result.headers.update({"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})
    return result


class GoogleExchange(BaseModel):
    ticket: str = Field(min_length=20, max_length=200)


async def _google_user(db: AsyncSession, identity: dict) -> dict:
    # Serialize subject/email claims against concurrent callback requests.
    await db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:email, 0))"),
        {"email": identity["email"]},
    )
    await db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:sub, 1))"), {"sub": identity["sub"]}
    )
    result = await db.execute(
        text(
            "SELECT u.* FROM users u JOIN oauth_identities o ON u.id=o.user_id WHERE o.provider='google' AND o.subject=:sub"
        ),
        identity,
    )
    user = result.mappings().first()
    if user is not None:
        return dict(user)
    result = await db.execute(text("SELECT * FROM users WHERE email=:email"), identity)
    user = result.mappings().first()
    if user is not None and not identity["authoritative_email"]:
        raise HTTPException(409, "sign_in_with_existing_method")
    if user is None:
        uid = uuid.uuid4()
        await db.execute(
            text(
                "INSERT INTO users (id,email,credits_balance,status) VALUES (:uid,:email,:credits,'active')"
            ),
            {"uid": uid, "email": identity["email"], "credits": settings.signup_grant_credits},
        )
        await db.execute(
            text(
                "INSERT INTO credit_transactions (id,user_id,delta,balance_after,type,idempotency_key) VALUES (:id,:uid,:credits,:credits,'grant',:key) ON CONFLICT (idempotency_key) DO NOTHING"
            ),
            {
                "id": uuid.uuid4(),
                "uid": uid,
                "credits": settings.signup_grant_credits,
                "key": f"signup_grant:{uid}",
            },
        )
        await initialize_preferences(db, uid, identity["locale"])
        result = await db.execute(text("SELECT * FROM users WHERE id=:uid"), {"uid": uid})
        user = result.mappings().one()
    await db.execute(
        text(
            "INSERT INTO oauth_identities (provider,subject,user_id) VALUES ('google',:sub,:uid) ON CONFLICT (provider,subject) DO NOTHING"
        ),
        {"sub": identity["sub"], "uid": user["id"]},
    )
    return dict(user)


@router.post("/exchange", response_model=TokenResponse)
@limiter.limit("10/minute")
async def google_exchange(
    request: Request, body: GoogleExchange, response: Response, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    _require_config()
    async with aioredis.from_url(settings.redis_url) as redis:
        raw = await redis.getdel(f"google:ticket:{body.ticket}")
    if raw is None:
        raise HTTPException(400, "google_ticket_expired")
    identity = json.loads(raw)
    if not hmac.compare_digest(identity["browser"], request.cookies.get(_COOKIE, "")):
        raise HTTPException(400, "invalid_google_browser")
    user = await _google_user(db, identity)
    if user["status"] != "active":
        # Use the existing recovery flow for deleted accounts; never silently reactivate.
        raise HTTPException(403, "sign_in_with_existing_method")
    uid = user["id"]
    token = auth_manager.create_access_token(str(uid), user["email"])
    refresh = secrets.token_hex(32)
    await db.execute(
        text(
            "INSERT INTO auth_sessions (id,user_id,refresh_token_hash,expires_at,user_agent,ip) VALUES (:id,:uid,:hash,:expires,:ua,:ip)"
        ),
        {
            "id": uuid.uuid4(),
            "uid": uid,
            "hash": hashlib.sha256(refresh.encode()).hexdigest(),
            "expires": datetime.now(timezone.utc)
            + timedelta(days=settings.refresh_token_expire_days),
            "ua": request.headers.get("user-agent"),
            "ip": request.client.host if request.client else None,
        },
    )
    await db.execute(text("UPDATE users SET last_login_at=NOW() WHERE id=:uid"), {"uid": uid})
    await db.commit()
    response.delete_cookie(_COOKIE, path="/api/auth/google")
    response.headers["Cache-Control"] = "no-store"
    return TokenResponse(
        access_token=token.access_token,
        refresh_token=refresh,
        expires_in=token.expires_in,
        user=UserResponse(
            id=str(uid),
            email=user["email"],
            display_name=user["display_name"],
            avatar_url=user["avatar_url"],
            gender=user["gender"],
            birthdate=str(user["birthdate"]) if user["birthdate"] else None,
            age_verified=user["age_verified_at"] is not None,
            credits_balance=user["credits_balance"] / 100,
            has_password=user["password_hash"] is not None,
        ),
        needs_profile=user["birthdate"] is None or user["age_verified_at"] is None,
    )
