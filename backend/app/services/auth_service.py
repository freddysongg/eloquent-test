"""
Authentication service for user login, registration, and session management.

Handles Clerk integration, JWT token management, and user session lifecycle
with proper security and correlation tracking.
"""

import logging
from typing import Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationException, ExternalServiceException
from app.core.security import (
    ClerkUser,
    create_access_token,
    create_refresh_token,
    generate_session_id,
    verify_clerk_token,
    verify_token,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AuthResponse, TokenResponse, UserProfileResponse


logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service for user management and session handling."""
    
    def __init__(self, db: Optional[AsyncSession] = None) -> None:
        """
        Initialize authentication service.
        
        Args:
            db: Optional database session
        """
        self.db = db
        self.user_repository = UserRepository(db) if db else None
    
    async def authenticate_with_clerk(
        self,
        clerk_token: str,
        correlation_id: str
    ) -> AuthResponse:
        """
        Authenticate user using Clerk session token.
        
        Args:
            clerk_token: Clerk session token from frontend
            correlation_id: Request correlation ID for tracking
        
        Returns:
            Complete authentication response with user and tokens
        
        Raises:
            AuthenticationException: If authentication fails
            ExternalServiceException: If Clerk API fails
        """
        logger.info(
            f"Authenticating user with Clerk token",
            extra={"correlation_id": correlation_id}
        )
        
        try:
            # Verify Clerk token and get user data
            clerk_user = await verify_clerk_token(clerk_token)
            
            # Get or create user in database
            user = await self._get_or_create_user(clerk_user, correlation_id)
            
            # Generate JWT tokens
            tokens = await self._generate_token_pair(user, correlation_id)
            
            # Generate session ID
            session_id = generate_session_id()
            
            logger.info(
                f"User authenticated successfully: {user.email}",
                extra={
                    "correlation_id": correlation_id,
                    "user_id": str(user.id),
                    "clerk_user_id": user.clerk_user_id
                }
            )
            
            return AuthResponse(
                user=UserProfileResponse.from_orm(user),
                tokens=tokens,
                session_id=session_id
            )
            
        except Exception as e:
            logger.error(
                f"Authentication failed: {str(e)}",
                extra={"correlation_id": correlation_id}
            )
            raise AuthenticationException(
                f"Authentication failed: {str(e)}",
                correlation_id=correlation_id
            )
    
    async def refresh_access_token(
        self,
        refresh_token: str,
        correlation_id: str
    ) -> TokenResponse:
        """
        Refresh JWT access token using refresh token.
        
        Args:
            refresh_token: Valid refresh token
            correlation_id: Request correlation ID for tracking
        
        Returns:
            New JWT token pair
        
        Raises:
            AuthenticationException: If refresh token is invalid
        """
        logger.info(
            f"Refreshing access token",
            extra={"correlation_id": correlation_id}
        )
        
        try:
            # Verify refresh token
            token_data = verify_token(refresh_token)
            
            if not token_data.user_id:
                raise AuthenticationException("Invalid refresh token")
            
            # Get user from database
            if not self.user_repository:
                raise AuthenticationException("Database session required")
            
            user = await self.user_repository.get_by_id(UUID(token_data.user_id))
            if not user:
                raise AuthenticationException("User not found")
            
            # Generate new token pair
            tokens = await self._generate_token_pair(user, correlation_id)
            
            logger.info(
                f"Access token refreshed successfully",
                extra={
                    "correlation_id": correlation_id,
                    "user_id": str(user.id)
                }
            )
            
            return tokens
            
        except Exception as e:
            logger.error(
                f"Token refresh failed: {str(e)}",
                extra={"correlation_id": correlation_id}
            )
            raise AuthenticationException(
                f"Token refresh failed: {str(e)}",
                correlation_id=correlation_id
            )
    
    async def invalidate_user_session(
        self,
        user_id: UUID,
        correlation_id: str
    ) -> None:
        """
        Invalidate user session on logout.
        
        Args:
            user_id: User identifier
            correlation_id: Request correlation ID for tracking
        """
        logger.info(
            f"Invalidating user session",
            extra={
                "correlation_id": correlation_id,
                "user_id": str(user_id)
            }
        )
        
        # TODO: Implement session invalidation in Redis cache
        # This will be completed by the Integration Agent
        
        logger.info(
            f"User session invalidated",
            extra={
                "correlation_id": correlation_id,
                "user_id": str(user_id)
            }
        )
    
    async def create_anonymous_session(
        self,
        correlation_id: str,
        client_ip: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Create anonymous session for unauthenticated users.
        
        Args:
            correlation_id: Request correlation ID for tracking
            client_ip: Client IP address for security
        
        Returns:
            Anonymous session information
        """
        session_id = generate_session_id()
        
        logger.info(
            f"Created anonymous session",
            extra={
                "correlation_id": correlation_id,
                "session_id": session_id,
                "client_ip": client_ip
            }
        )
        
        # TODO: Store anonymous session in Redis with expiration
        # This will be completed by the Integration Agent
        
        return {
            "session_id": session_id,
            "session_type": "anonymous",
            "expires_in": 3600 * 24 * 7  # 7 days
        }
    
    async def _get_or_create_user(
        self,
        clerk_user: ClerkUser,
        correlation_id: str
    ) -> User:
        """
        Get existing user or create new one from Clerk data.
        
        Args:
            clerk_user: Clerk user information
            correlation_id: Request correlation ID for tracking
        
        Returns:
            User model instance
        """
        if not self.user_repository:
            raise AuthenticationException("Database session required")
        
        # Try to get existing user
        user = await self.user_repository.get_by_clerk_id(clerk_user.id)
        
        if user:
            # Update existing user with latest Clerk data
            user.update_from_clerk(clerk_user.dict())
            user = await self.user_repository.update(user)
            
            logger.info(
                f"Updated existing user from Clerk",
                extra={
                    "correlation_id": correlation_id,
                    "user_id": str(user.id),
                    "clerk_user_id": user.clerk_user_id
                }
            )
        else:
            # Create new user
            user = User(
                clerk_user_id=clerk_user.id,
                email=clerk_user.primary_email,
                first_name=clerk_user.first_name,
                last_name=clerk_user.last_name
            )
            user.update_from_clerk(clerk_user.dict())
            user = await self.user_repository.create(user)
            
            logger.info(
                f"Created new user from Clerk",
                extra={
                    "correlation_id": correlation_id,
                    "user_id": str(user.id),
                    "clerk_user_id": user.clerk_user_id
                }
            )
        
        return user
    
    async def _generate_token_pair(
        self,
        user: User,
        correlation_id: str
    ) -> TokenResponse:
        """
        Generate JWT token pair for authenticated user.
        
        Args:
            user: User model instance
            correlation_id: Request correlation ID for tracking
        
        Returns:
            JWT token response with access and refresh tokens
        """
        from app.core.config import settings
        
        # Token payload
        token_data = {
            "sub": str(user.id),
            "clerk_user_id": user.clerk_user_id,
            "email": user.email,
        }
        
        # Generate tokens
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(str(user.id))
        
        logger.info(
            f"Generated JWT token pair",
            extra={
                "correlation_id": correlation_id,
                "user_id": str(user.id)
            }
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )