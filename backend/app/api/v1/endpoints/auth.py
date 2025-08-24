"""
Authentication endpoints for user login, registration, and token management.

Handles Clerk integration, JWT tokens, and session management for both
authenticated and anonymous users.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user, require_authenticated_user
from app.api.dependencies.common import RequestContext, get_request_context
from app.core.exceptions import AuthenticationException
from app.models.base import get_db_session
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    LogoutResponse,
    TokenRefreshRequest,
    TokenResponse,
    UserProfileResponse,
)
from app.services.auth_service import AuthService


router = APIRouter()


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db_session),
    context: RequestContext = Depends(get_request_context)
) -> AuthResponse:
    """
    Authenticate user with Clerk session token.
    
    Args:
        request: Login request with Clerk session token
        db: Database session
        context: Request context for logging
    
    Returns:
        Authentication response with JWT tokens and user data
    
    Raises:
        AuthenticationException: If authentication fails
    """
    auth_service = AuthService(db)
    
    try:
        auth_response = await auth_service.authenticate_with_clerk(
            clerk_token=request.clerk_session_token,
            correlation_id=context.correlation_id
        )
        
        return auth_response
        
    except Exception as e:
        raise AuthenticationException(
            f"Login failed: {str(e)}",
            correlation_id=context.correlation_id
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db_session),
    context: RequestContext = Depends(get_request_context)
) -> TokenResponse:
    """
    Refresh JWT access token using refresh token.
    
    Args:
        request: Token refresh request with refresh token
        db: Database session
        context: Request context for logging
    
    Returns:
        New JWT token pair
    
    Raises:
        AuthenticationException: If refresh token is invalid
    """
    auth_service = AuthService(db)
    
    try:
        token_response = await auth_service.refresh_access_token(
            refresh_token=request.refresh_token,
            correlation_id=context.correlation_id
        )
        
        return token_response
        
    except Exception as e:
        raise AuthenticationException(
            f"Token refresh failed: {str(e)}",
            correlation_id=context.correlation_id
        )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    response: Response,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    context: RequestContext = Depends(get_request_context)
) -> LogoutResponse:
    """
    Logout user and invalidate session.
    
    Args:
        response: HTTP response for cookie clearing
        current_user: Current authenticated user
        db: Database session
        context: Request context for logging
    
    Returns:
        Logout confirmation response
    """
    auth_service = AuthService(db)
    
    # Clear session cookies
    response.delete_cookie("session_id")
    response.delete_cookie("access_token")
    
    if current_user:
        # Invalidate user session in database/cache
        await auth_service.invalidate_user_session(
            user_id=current_user.id,
            correlation_id=context.correlation_id
        )
    
    return LogoutResponse(
        message="Logout successful",
        logged_out=True
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    current_user: User = Depends(require_authenticated_user),
    context: RequestContext = Depends(get_request_context)
) -> UserProfileResponse:
    """
    Get current user profile information.
    
    Args:
        current_user: Authenticated user
        context: Request context for logging
    
    Returns:
        User profile data
    """
    return UserProfileResponse(
        id=current_user.id,
        clerk_user_id=current_user.clerk_user_id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        full_name=current_user.full_name,
        display_name=current_user.display_name,
        avatar_url=current_user.avatar_url,
        is_verified=current_user.is_verified,
        preferences=current_user.preferences,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )


@router.post("/anonymous-session")
async def create_anonymous_session(
    response: Response,
    context: RequestContext = Depends(get_request_context)
) -> dict:
    """
    Create anonymous session for unauthenticated users.
    
    Args:
        response: HTTP response for cookie setting
        context: Request context for logging
    
    Returns:
        Anonymous session information
    """
    auth_service = AuthService()
    
    # Generate anonymous session
    session_data = await auth_service.create_anonymous_session(
        correlation_id=context.correlation_id,
        client_ip=context.client_ip
    )
    
    # Set session cookie
    response.set_cookie(
        key="session_id",
        value=session_data["session_id"],
        max_age=3600 * 24 * 7,  # 7 days
        httponly=True,
        secure=True,
        samesite="strict"
    )
    
    return session_data


@router.get("/session-status")
async def get_session_status(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    context: RequestContext = Depends(get_request_context)
) -> dict:
    """
    Get current session status and user information.
    
    Args:
        request: FastAPI request object
        current_user: Current authenticated user (optional)
        context: Request context for logging
    
    Returns:
        Session status information
    """
    session_id = request.cookies.get("session_id")
    
    if current_user:
        return {
            "authenticated": True,
            "user_id": str(current_user.id),
            "session_type": "authenticated",
            "user": {
                "email": current_user.email,
                "full_name": current_user.full_name,
                "avatar_url": current_user.avatar_url
            }
        }
    elif session_id:
        return {
            "authenticated": False,
            "session_id": session_id,
            "session_type": "anonymous"
        }
    else:
        return {
            "authenticated": False,
            "session_type": "none"
        }