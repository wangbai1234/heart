"""JWT authentication module for Heart API."""

from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from pydantic import BaseModel, EmailStr
from fastapi import HTTPException, status
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

    def __init__(self, secret_key: str, algorithm: str = "HS256", expire_minutes: int = 43200):
        """Initialize auth manager.

        Args:
            secret_key: Secret key for signing tokens
            algorithm: JWT algorithm (default: HS256)
            expire_minutes: Token expiration time in minutes (default: 30 days)
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expire_minutes = expire_minutes

    def create_access_token(self, user_id: str, email: Optional[str] = None) -> Token:
        """Create a JWT access token.

        Args:
            user_id: User ID
            email: Optional email address

        Returns:
            Token object with access token and expiration
        """
        expires = datetime.now(timezone.utc) + timedelta(minutes=self.expire_minutes)

        payload = {
            "sub": user_id,
            "email": email,
            "exp": int(expires.timestamp()),
            "iat": int(datetime.now(timezone.utc).timestamp()),
        }

        encoded_jwt = jwt.encode(
            payload,
            self.secret_key,
            algorithm=self.algorithm,
        )

        return Token(
            access_token=encoded_jwt,
            token_type="bearer",
            expires_in=self.expire_minutes * 60,
        )

    def verify_token(self, token: str) -> TokenData:
        """Verify and decode JWT token.

        Args:
            token: JWT token string

        Returns:
            TokenData with user_id and email

        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
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

            token_data = TokenData(
                user_id=user_id,
                email=email,
                exp=datetime.fromtimestamp(exp, tz=timezone.utc) if exp else None,
            )
            return token_data

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except (jwt.DecodeError, jwt.InvalidSignatureError, jwt.InvalidTokenError) as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def refresh_token(self, token: str) -> Token:
        """Refresh an existing token.

        Args:
            token: Current JWT token

        Returns:
            New Token object
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
    expire_minutes=settings.access_token_expire_minutes,
)
