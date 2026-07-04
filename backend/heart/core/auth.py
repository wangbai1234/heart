"""JWT authentication module for Heart/yuoyuo API.

Supports RS256 (default) and HS256. Access tokens are short-lived (30min).
Refresh tokens are managed via auth_sessions table (see routes_auth.py).
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Header, HTTPException, status
from pydantic import BaseModel

from .config import settings


class TokenData(BaseModel):
    """Token payload data."""

    user_id: str
    email: Optional[str] = None
    exp: Optional[datetime] = None


class User(BaseModel):
    """User model."""

    user_id: str
    email: str
    username: str
    is_active: bool = True


class Token(BaseModel):
    """Token response model."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthManager:
    """Manages JWT token generation and verification."""

    def __init__(
        self,
        secret_key: str = "",
        algorithm: str = "RS256",
        private_key: str = "",
        public_key: str = "",
        expire_minutes: int = 30,
    ):
        self.algorithm = algorithm
        self.expire_minutes = expire_minutes

        if algorithm == "RS256":
            if not private_key or not public_key:
                raise ValueError("RS256 requires jwt_private_key and jwt_public_key")
            self._sign_key = private_key
            self._verify_key = public_key
        else:
            self._sign_key = secret_key
            self._verify_key = secret_key

    def create_access_token(self, user_id: str, email: Optional[str] = None) -> Token:
        """Create a short-lived JWT access token.

        Claims: sub (user_id), email, exp, iat, typ="access"
        """
        expires = datetime.now(timezone.utc) + timedelta(minutes=self.expire_minutes)

        payload = {
            "sub": user_id,
            "email": email,
            "exp": int(expires.timestamp()),
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "typ": "access",
        }

        encoded_jwt = jwt.encode(
            payload,
            self._sign_key,
            algorithm=self.algorithm,
        )

        return Token(
            access_token=encoded_jwt,
            token_type="bearer",
            expires_in=self.expire_minutes * 60,
        )

    def verify_token(self, token: str) -> TokenData:
        """Verify and decode JWT token.

        Returns TokenData with user_id and email.
        Raises HTTPException 401 if invalid or expired.
        """
        try:
            payload = jwt.decode(
                token,
                self._verify_key,
                algorithms=[self.algorithm],
            )
            user_id: str = payload.get("sub")
            email: Optional[str] = payload.get("email")
            exp: Optional[int] = payload.get("exp")

            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing user_id",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return TokenData(
                user_id=user_id,
                email=email,
                exp=datetime.fromtimestamp(exp, tz=timezone.utc) if exp else None,
            )

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            ) from None
        except (jwt.DecodeError, jwt.InvalidSignatureError, jwt.InvalidTokenError) as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e

    def refresh_token(self, token: str) -> Token:
        """Refresh an existing token (verify + re-issue).

        Convenience method for backward compatibility.
        For production refresh with rotation, use routes_auth.py.
        """
        token_data = self.verify_token(token)
        return self.create_access_token(
            user_id=token_data.user_id,
            email=token_data.email,
        )


# Global auth manager instance
auth_manager = AuthManager(
    secret_key=settings.jwt_secret_key,
    algorithm=settings.jwt_algorithm,
    private_key=settings.jwt_private_key,
    public_key=settings.jwt_public_key,
    expire_minutes=settings.access_token_expire_minutes,
)


async def get_current_user(authorization: Optional[str] = Header(None)) -> TokenData:
    """FastAPI dependency: extract and verify JWT from Authorization header.

    Returns TokenData with user_id.
    Raises HTTPException 401 if missing/invalid token.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth_manager.verify_token(parts[1])
