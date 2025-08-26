"""
Authentication dependencies for API endpoints.

Provides user authentication, session management, and authorization
checks for protected endpoints.
"""

from typing import Optional

import structlog
from fastapi import Depends, HTTPException, Request, WebSocket
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationException, AuthorizationException
from app.core.security import generate_session_id, verify_clerk_token, verify_token
from app.models.base import get_db_session
from app.models.user import User
from app.repositories.user_repository import UserRepository

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)

# Initialize logger
logger = structlog.get_logger(__name__)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session),
) -> Optional[User]:
    """
    Get current authenticated user from JWT token.

    Args:
        request: FastAPI request object
        credentials: HTTP Bearer credentials
        db: Database session

    Returns:
        Authenticated user or None for anonymous access

    Raises:
        AuthenticationException: If token is invalid
    """
    if not credentials:
        return None

    try:
        # First try to verify as Clerk token
        try:
            clerk_user = await verify_clerk_token(credentials.credentials)

            # Get or create user from Clerk data
            user_repo = UserRepository(db)
            user = await user_repo.get_by_clerk_id(clerk_user.id)

            if not user:
                # Create new user from Clerk data
                user = User(
                    clerk_user_id=clerk_user.id,
                    email=clerk_user.primary_email,
                    first_name=clerk_user.first_name,
                    last_name=clerk_user.last_name,
                )
                user = await user_repo.create(user)
            else:
                # Update existing user with latest Clerk data
                user.update_from_clerk(clerk_user.dict())
                user = await user_repo.update(user)

            return user

        except HTTPException:
            # If Clerk token fails, try JWT token
            token_data = verify_token(credentials.credentials)

            if token_data.clerk_user_id:
                user_repo = UserRepository(db)
                user = await user_repo.get_by_clerk_id(token_data.clerk_user_id)

                if not user:
                    raise AuthenticationException("User not found")

                return user

            return None

    except Exception as e:
        raise AuthenticationException(f"Authentication failed: {str(e)}")


async def require_authenticated_user(
    current_user: Optional[User] = Depends(get_current_user),
) -> User:
    """
    Require authenticated user for protected endpoints.

    Args:
        current_user: Current user from authentication

    Returns:
        Authenticated user instance

    Raises:
        AuthenticationException: If user is not authenticated
    """
    if not current_user:
        raise AuthenticationException("Authentication required")

    if not current_user.is_active:
        raise AuthorizationException("Account is inactive")

    return current_user


async def get_session_id(
    request: Request, current_user: Optional[User] = Depends(get_current_user)
) -> str:
    """
    Get session identifier for user or anonymous session.

    Args:
        request: FastAPI request object
        current_user: Current authenticated user

    Returns:
        Session identifier string
    """
    if current_user:
        # For authenticated users, use user ID as session
        return str(current_user.id)
    else:
        # For anonymous users, get or generate session ID
        session_id = request.cookies.get("session_id")
        if not session_id:
            session_id = generate_session_id()
        return session_id


async def get_user_or_session(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_current_user),
) -> tuple[Optional[User], str]:
    """
    Get authenticated user or anonymous session information.

    Args:
        request: FastAPI request object
        db: Database session
        current_user: Current authenticated user

    Returns:
        Tuple of (user, session_id) for chat identification
    """
    session_id = await get_session_id(request, current_user)
    return current_user, session_id


def require_active_user(user: User = Depends(require_authenticated_user)) -> User:
    """
    Require active authenticated user.

    Args:
        user: Authenticated user

    Returns:
        Active user instance

    Raises:
        AuthorizationException: If user account is not active
    """
    if not user.is_active:
        raise AuthorizationException("Account is inactive")

    return user


def require_verified_user(user: User = Depends(require_active_user)) -> User:
    """
    Require verified authenticated user.

    Args:
        user: Active authenticated user

    Returns:
        Verified user instance

    Raises:
        AuthorizationException: If user email is not verified
    """
    if not user.is_verified:
        raise AuthorizationException("Email verification required")

    return user


async def get_optional_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session),
) -> Optional[User]:
    """
    Get current authenticated user from JWT token, allowing anonymous access.

    This is a variant of get_current_user that doesn't raise an exception
    when no authentication is provided, making it suitable for endpoints
    that support both authenticated and anonymous users.

    Args:
        request: FastAPI request object
        credentials: HTTP Bearer credentials (optional)
        db: Database session

    Returns:
        Authenticated user or None for anonymous access
    """
    try:
        return await get_current_user(request, credentials, db)
    except AuthenticationException:
        # Return None for anonymous access when authentication fails
        return None


async def get_websocket_user(
    websocket: "WebSocket", correlation_id: str = ""
) -> tuple[Optional[User], str]:
    """
    Authenticate WebSocket connection and return user or anonymous session.

    Extracts JWT token from WebSocket headers or query parameters and validates it.
    If no valid token is found, generates anonymous session identifier.

    Args:
        websocket: WebSocket connection instance
        correlation_id: Request correlation ID for tracking

    Returns:
        Tuple of (authenticated_user, session_id) where user is None for anonymous

    Raises:
        WebSocketException: If authentication fails due to invalid token
    """
    from app.models.base import get_db_session

    # Try to extract token from Authorization header
    auth_header = websocket.headers.get("Authorization")
    token = None

    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]  # Remove "Bearer " prefix
    else:
        # Try to extract from query parameters as fallback
        token = websocket.query_params.get("token")

    if not token:
        # No token provided - return anonymous session
        session_id = websocket.query_params.get("session_id") or generate_session_id()
        logger.info(
            f"WebSocket anonymous connection",
            extra={"correlation_id": correlation_id, "session_id": session_id},
        )
        return None, session_id

    try:
        # Get database session for user lookup
        db = await get_db_session().__anext__()

        try:
            # First try to verify as Clerk token
            try:
                clerk_user = await verify_clerk_token(token)

                # Get or create user from Clerk data
                user_repo = UserRepository(db)
                user = await user_repo.get_by_clerk_id(clerk_user.id)

                if not user:
                    # Create new user from Clerk data
                    user = User(
                        clerk_user_id=clerk_user.id,
                        email=clerk_user.primary_email,
                        first_name=clerk_user.first_name,
                        last_name=clerk_user.last_name,
                    )
                    user = await user_repo.create(user)
                else:
                    # Update existing user with latest Clerk data
                    user.update_from_clerk(clerk_user.dict())
                    user = await user_repo.update(user)

                logger.info(
                    f"WebSocket authenticated via Clerk token",
                    extra={
                        "correlation_id": correlation_id,
                        "user_id": str(user.id),
                        "clerk_user_id": user.clerk_user_id,
                    },
                )

                return user, str(user.id)

            except HTTPException:
                # If Clerk token fails, try JWT token
                token_data = verify_token(token)

                if token_data.clerk_user_id:
                    user_repo = UserRepository(db)
                    user = await user_repo.get_by_clerk_id(token_data.clerk_user_id)

                    if not user:
                        logger.warning(
                            f"JWT token valid but user not found",
                            extra={
                                "correlation_id": correlation_id,
                                "clerk_user_id": token_data.clerk_user_id,
                            },
                        )
                        # Return anonymous session if user not found
                        session_id = generate_session_id()
                        return None, session_id

                    if not user.is_active:
                        logger.warning(
                            f"WebSocket connection attempt by inactive user",
                            extra={
                                "correlation_id": correlation_id,
                                "user_id": str(user.id),
                            },
                        )
                        # Return anonymous session for inactive users
                        session_id = generate_session_id()
                        return None, session_id

                    logger.info(
                        f"WebSocket authenticated via JWT token",
                        extra={
                            "correlation_id": correlation_id,
                            "user_id": str(user.id),
                        },
                    )

                    return user, str(user.id)

                # Token doesn't contain user info - return anonymous
                session_id = generate_session_id()
                return None, session_id

        finally:
            # Ensure database session is properly closed
            try:
                await db.close()
            except Exception as close_error:
                logger.warning(
                    f"Failed to close WebSocket auth db session: {close_error}"
                )

    except Exception as e:
        logger.error(
            f"WebSocket authentication error: {str(e)}",
            extra={"correlation_id": correlation_id},
        )

        # On authentication error, allow anonymous connection
        session_id = generate_session_id()
        return None, session_id
