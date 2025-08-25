"""
Authentication request/response schemas.

Pydantic models for authentication endpoints with proper validation
and serialization for JWT tokens and user data.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Login request with Clerk session token."""

    clerk_session_token: str = Field(
        ..., description="Clerk session token from frontend authentication"
    )


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str = Field(
        ..., description="JWT access token for API authentication"
    )

    refresh_token: str = Field(..., description="JWT refresh token for token renewal")

    token_type: str = Field(
        default="bearer", description="Token type for Authorization header"
    )

    expires_in: int = Field(..., description="Access token expiration time in seconds")


class TokenRefreshRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str = Field(
        ..., description="Valid refresh token for access token renewal"
    )


class UserProfileResponse(BaseModel):
    """User profile response."""

    id: UUID = Field(..., description="User unique identifier")

    clerk_user_id: str = Field(..., description="Clerk user identifier")

    email: Optional[str] = Field(None, description="User's primary email address")

    first_name: Optional[str] = Field(None, description="User's first name")

    last_name: Optional[str] = Field(None, description="User's last name")

    full_name: str = Field(..., description="User's full name (computed)")

    display_name: Optional[str] = Field(
        None, description="User's preferred display name"
    )

    avatar_url: Optional[str] = Field(None, description="URL to user's profile avatar")

    is_verified: bool = Field(..., description="Whether user's email is verified")

    preferences: Dict[str, Any] = Field(
        default_factory=dict, description="User preferences and settings"
    )

    created_at: datetime = Field(..., description="Account creation timestamp")

    updated_at: datetime = Field(..., description="Last account update timestamp")


class AuthResponse(BaseModel):
    """Complete authentication response."""

    user: UserProfileResponse = Field(..., description="Authenticated user profile")

    tokens: TokenResponse = Field(..., description="JWT token pair")

    session_id: str = Field(..., description="Session identifier")


class LogoutResponse(BaseModel):
    """Logout response."""

    message: str = Field(
        default="Logout successful", description="Logout status message"
    )

    logged_out: bool = Field(default=True, description="Whether logout was successful")
