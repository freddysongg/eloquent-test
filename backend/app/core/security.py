"""
Security utilities for authentication, authorization, and token management.

Implements JWT token handling, Clerk integration, and security middleware
with proper type hints and error handling.
"""

import base64
import json as json_lib
import logging
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException, status
from jose import JWTError, jwk
from jose import jwt
from jose import jwt as jose_jwt
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
    Verify Clerk session token using JWT verification (recommended approach).

    Implements proper JWT token verification using Clerk's public key instead of
    API calls. This is more efficient and follows Clerk's recommended practices.

    Args:
        token: Clerk session token (JWT) from frontend

    Returns:
        Clerk user data

    Raises:
        HTTPException: If token verification fails
    """
    # Development mode bypass for testing
    if settings.ENVIRONMENT == "development" and settings.CLERK_SECRET_KEY in [
        "sk_test_development",
        "development",
    ]:
        # Return mock user for development
        return ClerkUser(
            id=f"user_development_{token[:8]}",
            email_addresses=[
                {
                    "id": "email_1",
                    "primary_email_address_id": "email_1",
                    "email_address": "dev@eloquentai.com",
                }
            ],
            first_name="Development",
            last_name="User",
            created_at=int(datetime.utcnow().timestamp()),
            updated_at=int(datetime.utcnow().timestamp()),
        )

    try:
        # Step 1: Decode JWT header to extract key ID
        try:
            # Split JWT into parts
            header_b64, payload_b64, signature_b64 = token.split(".")

            # Add padding if needed for base64 decoding
            header_b64_padded = header_b64 + "=" * (4 - len(header_b64) % 4)
            header_bytes = base64.urlsafe_b64decode(header_b64_padded)
            header = json_lib.loads(header_bytes.decode("utf-8"))

            kid = header.get("kid")
            if not kid:
                raise ValueError("JWT header missing 'kid' claim")

        except (ValueError, json_lib.JSONDecodeError) as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid JWT format: {str(e)}",
            )

        # Step 2: Get Clerk's public keys from JWKS endpoint
        async with httpx.AsyncClient() as client:
            # Construct JWKS URL from issuer
            # Extract issuer from token payload first to determine correct JWKS endpoint
            payload_b64_padded = payload_b64 + "=" * (4 - len(payload_b64) % 4)
            payload_bytes = base64.urlsafe_b64decode(payload_b64_padded)
            payload = json_lib.loads(payload_bytes.decode("utf-8"))

            issuer = payload.get("iss")
            if not issuer:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="JWT missing issuer claim",
                )

            # Construct JWKS URL
            jwks_url = f"{issuer}/.well-known/jwks.json"

            try:
                jwks_response = await client.get(jwks_url, timeout=5.0)
                jwks_response.raise_for_status()
                jwks = jwks_response.json()
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Failed to fetch JWKS: {str(e)}",
                )

        # Step 3: Find matching public key
        public_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                # Convert JWK to PEM format using jose library
                public_key = jwk.construct(key).to_pem()
                break

        if not public_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Public key not found for kid: {kid}",
            )

        # Step 4: Verify JWT signature and claims
        try:
            # Verify token with public key
            decoded_token = jose_jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                issuer=issuer,
                options={
                    "verify_signature": True,
                    "verify_aud": False,  # Clerk doesn't use aud claim
                    "verify_iss": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                },
            )
        except jose_jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired. Please sign in again.",
            )
        except jose_jwt.JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token verification failed: {str(e)}",
            )

        # Step 5: Additional validation
        current_time = int(datetime.utcnow().timestamp())

        # Check expiration
        exp = decoded_token.get("exp")
        if exp and current_time >= exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
            )

        # Check not before
        nbf = decoded_token.get("nbf")
        if nbf and current_time < nbf:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token not yet valid"
            )

        # Validate authorized party (azp) claim
        azp = decoded_token.get("azp")
        if azp and azp not in settings.CORS_ORIGINS:
            # Log warning but don't block - might be legitimate
            logger = logging.getLogger(__name__)
            logger.warning(f"Token azp claim '{azp}' not in allowed origins")

        # Step 6: Extract user information and fetch user details if needed
        user_id = decoded_token.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing user ID claim",
            )

        # For now, extract available user info from token
        # In production, you might want to fetch fresh user data from Clerk API
        session_id = decoded_token.get("sid")

        # Create minimal user object from token claims
        # Note: JWT doesn't contain full user details, you may need to fetch from API
        return ClerkUser(
            id=user_id,
            email_addresses=[],  # Would need API call to get email details
            first_name=None,  # Would need API call for full profile
            last_name=None,  # Would need API call for full profile
            created_at=decoded_token.get("iat", current_time),
            updated_at=current_time,
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {str(e)}",
        )


async def fetch_clerk_user_details(user_id: str) -> ClerkUser:
    """
    Fetch complete user details from Clerk API using user ID.

    This function should be used when you need full user profile information
    beyond what's available in the JWT token claims.

    Args:
        user_id: Clerk user ID from verified token

    Returns:
        Complete Clerk user data

    Raises:
        HTTPException: If user fetch fails
    """
    try:
        headers = {
            "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            user_url = f"https://api.clerk.dev/v1/users/{user_id}"
            response = await client.get(user_url, headers=headers, timeout=10.0)

            if response.status_code == 200:
                user_data = response.json()
                return ClerkUser(**user_data)
            elif response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User not found: {user_id}",
                )
            elif response.status_code == 410:
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail=f"User permanently deleted: {user_id}",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Failed to fetch user: {response.status_code}",
                )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Clerk API request failed: {str(e)}",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error fetching user: {str(e)}",
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
