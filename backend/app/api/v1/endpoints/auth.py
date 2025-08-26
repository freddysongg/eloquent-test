"""
Authentication endpoints for user login, registration, and token management.

Handles Clerk integration, JWT tokens, and session management for both
authenticated and anonymous users.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
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
logger = logging.getLogger(__name__)


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db_session),
    context: RequestContext = Depends(get_request_context),
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
            correlation_id=context.correlation_id,
        )

        return auth_response

    except Exception as e:
        raise AuthenticationException(
            f"Login failed: {str(e)}", correlation_id=context.correlation_id
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db_session),
    context: RequestContext = Depends(get_request_context),
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
            refresh_token=request.refresh_token, correlation_id=context.correlation_id
        )

        return token_response

    except Exception as e:
        raise AuthenticationException(
            f"Token refresh failed: {str(e)}", correlation_id=context.correlation_id
        )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    response: Response,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    context: RequestContext = Depends(get_request_context),
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
            user_id=current_user.id, correlation_id=context.correlation_id
        )

    return LogoutResponse(message="Logout successful", logged_out=True)


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    current_user: User = Depends(require_authenticated_user),
    context: RequestContext = Depends(get_request_context),
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
        updated_at=current_user.updated_at,
    )


@router.post("/anonymous-session")
async def create_anonymous_session(
    response: Response, context: RequestContext = Depends(get_request_context)
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
        correlation_id=context.correlation_id, client_ip=context.client_ip
    )

    # Set session cookie
    response.set_cookie(
        key="session_id",
        value=session_data["session_id"],
        max_age=3600 * 24 * 7,  # 7 days
        httponly=True,
        secure=True,
        samesite="strict",
    )

    return session_data


@router.get("/session-status")
async def get_session_status(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    context: RequestContext = Depends(get_request_context),
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
                "avatar_url": current_user.avatar_url,
            },
        }
    elif session_id:
        return {
            "authenticated": False,
            "session_id": session_id,
            "session_type": "anonymous",
        }
    else:
        return {"authenticated": False, "session_type": "none"}


@router.post("/migrate-anonymous")
async def migrate_anonymous_data(
    request: Request,
    current_user: User = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db_session),
    context: RequestContext = Depends(get_request_context),
) -> dict:
    """
    Migrate anonymous user data to authenticated user account.

    Transfers chat history and preferences from anonymous session to
    the newly authenticated user account with full data integrity.

    Args:
        request: FastAPI request object
        current_user: Authenticated user to migrate data to
        db: Database session
        context: Request context for logging

    Returns:
        Migration status and summary
    """
    from app.repositories.chat_repository import ChatRepository
    from app.repositories.message_repository import MessageRepository

    try:
        migration_data = await request.json()
        anonymous_session_id = migration_data.get("anonymousSessionId", "")

        if not anonymous_session_id:
            raise HTTPException(
                status_code=400, detail="Anonymous session ID is required for migration"
            )

        logger.info(
            f"Starting anonymous data migration for user {current_user.id}",
            extra={
                "correlation_id": context.correlation_id,
                "user_id": str(current_user.id),
                "anonymous_session_id": anonymous_session_id,
            },
        )

        # Initialize repositories for migration
        chat_repo = ChatRepository(db)
        message_repo = MessageRepository(db)

        migration_summary = {
            "chats_migrated": 0,
            "messages_migrated": 0,
            "errors": [],
        }

        # 1. Find all anonymous chats by session ID
        anonymous_chats = await chat_repo.list_by_session(
            session_id=anonymous_session_id,
            limit=100,  # Reasonable limit for anonymous chats
            include_archived=True,
        )

        logger.info(
            f"Found {len(anonymous_chats)} anonymous chats to migrate",
            extra={
                "correlation_id": context.correlation_id,
                "anonymous_session_id": anonymous_session_id,
                "chat_count": len(anonymous_chats),
            },
        )

        # 2. Transfer each chat to the authenticated user
        for chat in anonymous_chats:
            try:
                # Update chat ownership
                chat.user_id = current_user.id
                chat.session_id = None  # Clear session ID since it's now owned by user

                # Update chat title if it's a default anonymous title
                if chat.title in ["New Chat", "Anonymous Chat", ""]:
                    # Get first message to create a better title
                    messages = await message_repo.list_by_chat(
                        chat_id=chat.id, limit=1, offset=0
                    )
                    if messages and len(messages[0].content) > 0:
                        # Create title from first 50 characters of first message
                        title_text = messages[0].content[:50].strip()
                        if len(messages[0].content) > 50:
                            title_text += "..."
                        chat.title = title_text
                    else:
                        chat.title = (
                            f"Migrated Chat #{migration_summary['chats_migrated'] + 1}"
                        )

                # Save updated chat
                await chat_repo.update(chat)
                migration_summary["chats_migrated"] += 1

                # 3. Count messages for this chat (they automatically belong to user now)
                chat_messages = await message_repo.list_by_chat(
                    chat_id=chat.id, limit=1000  # Count all messages
                )
                migration_summary["messages_migrated"] += len(chat_messages)

                logger.debug(
                    f"Migrated chat {chat.id} with {len(chat_messages)} messages",
                    extra={
                        "correlation_id": context.correlation_id,
                        "chat_id": str(chat.id),
                        "message_count": len(chat_messages),
                    },
                )

            except Exception as chat_error:
                error_msg = f"Failed to migrate chat {chat.id}: {str(chat_error)}"
                migration_summary["errors"].append(error_msg)
                logger.error(
                    error_msg,
                    extra={
                        "correlation_id": context.correlation_id,
                        "chat_id": str(chat.id),
                    },
                )

        # 4. Commit all changes to database
        await db.commit()

        # 5. Log successful migration
        logger.info(
            f"Anonymous data migration completed successfully",
            extra={
                "correlation_id": context.correlation_id,
                "user_id": str(current_user.id),
                "anonymous_session_id": anonymous_session_id,
                "chats_migrated": migration_summary["chats_migrated"],
                "messages_migrated": migration_summary["messages_migrated"],
                "errors_count": len(migration_summary["errors"]),
            },
        )

        return {
            "status": "success",
            "message": "Anonymous data migration completed",
            "user_id": str(current_user.id),
            "anonymous_session_id": anonymous_session_id,
            "summary": migration_summary,
            "correlation_id": context.correlation_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        # Rollback transaction on error
        await db.rollback()

        logger.error(
            f"Anonymous data migration failed: {str(e)}",
            extra={
                "correlation_id": context.correlation_id,
                "user_id": str(current_user.id),
            },
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Migration failed",
                "error": str(e),
                "correlation_id": context.correlation_id,
            },
        )
