"""
Security utilities for authentication, authorization, and token management.

Implements JWT token handling, Clerk integration, and security middleware
with proper type hints and error handling.
"""

import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.core.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenData(BaseModel):
    """JWT token payload data structure."""

    user_id: Optional[str] = None
    clerk_user_id: Optional[str] = None
    email: Optional[str] = None
    session_id: Optional[str] = None
    exp: Optional[int] = None
    iat: Optional[int] = None
    iss: Optional[str] = None


class ClerkUser(BaseModel):
    """Clerk user data structure."""

    id: str
    email_addresses: list[Dict[str, Any]]
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    created_at: int
    updated_at: int

    @property
    def primary_email(self) -> Optional[str]:
        """Get primary email address."""
        for email in self.email_addresses:
            if email.get("id") == email.get("primary_email_address_id"):
                return email.get("email_address")
        return None


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token with expiration.

    Args:
        data: Token payload data
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string

    Raises:
        ValueError: If token creation fails
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update(
        {
            "exp": expire,
            "iat": datetime.utcnow(),
            "iss": settings.APP_NAME,
            "jti": str(uuid.uuid4()),
        }
    )

    try:
        encoded_jwt = jwt.encode(
            to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )
        return encoded_jwt
    except Exception as e:
        raise ValueError(f"Failed to create access token: {str(e)}")


def create_refresh_token(user_id: str) -> str:
    """
    Create JWT refresh token with extended expiration.

    Args:
        user_id: User identifier

    Returns:
        Encoded JWT refresh token

    Raises:
        ValueError: If token creation fails
    """
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
        "jti": str(uuid.uuid4()),
    }

    try:
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    except Exception as e:
        raise ValueError(f"Failed to create refresh token: {str(e)}")


def verify_token(token: str) -> TokenData:
    """
    Verify and decode JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded token data

    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        # Validate token structure
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception

        return TokenData(
            user_id=user_id,
            clerk_user_id=payload.get("clerk_user_id"),
            email=payload.get("email"),
            session_id=payload.get("session_id"),
            exp=payload.get("exp"),
            iat=payload.get("iat"),
            iss=payload.get("iss"),
        )

    except JWTError:
        raise credentials_exception


async def verify_clerk_token(token: str) -> ClerkUser:
    """
    Verify Clerk JWT token and fetch user data.

    Args:
        token: Clerk session token

    Returns:
        Clerk user data

    Raises:
        HTTPException: If token verification fails
    """
    try:
        # Clerk JWT verification endpoint
        verify_url = f"https://api.clerk.dev/v1/sessions/verify"

        headers = {
            "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}",
            "Content-Type": "application/json",
        }

        payload = {"token": token}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                verify_url, headers=headers, json=payload, timeout=10.0
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Clerk session token",
                )

            session_data = response.json()
            user_id = session_data.get("user_id")

            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="No user ID in Clerk session",
                )

            # Fetch user details
            user_url = f"https://api.clerk.dev/v1/users/{user_id}"
            user_response = await client.get(user_url, headers=headers, timeout=10.0)

            if user_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Failed to fetch user data from Clerk",
                )

            user_data = user_response.json()
            return ClerkUser(**user_data)

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Clerk API request failed: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {str(e)}",
        )


def generate_session_id() -> str:
    """
    Generate secure session ID for anonymous users.

    Returns:
        Secure random session ID string
    """
    return secrets.token_urlsafe(32)


def hash_password(password: str) -> str:
    """
    Hash password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hash.

    Args:
        plain_password: Plain text password
        hashed_password: Previously hashed password

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def generate_correlation_id() -> str:
    """
    Generate correlation ID for request tracking.

    Returns:
        UUID4 string for request correlation
    """
    return str(uuid.uuid4())


class SecurityHeaders:
    """Security headers for HTTP responses."""

    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """
        Get recommended security headers.

        Returns:
            Dictionary of security headers
        """
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }
