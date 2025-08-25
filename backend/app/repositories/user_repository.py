"""
User repository for database operations.

Provides CRUD operations and queries for User model with proper
async support and error handling.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User


class UserRepository:
    """Repository for User model database operations."""

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize user repository.

        Args:
            db: Async database session
        """
        self.db = db

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User UUID

        Returns:
            User model instance or None if not found
        """
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_clerk_id(self, clerk_user_id: str) -> Optional[User]:
        """
        Get user by Clerk user ID.

        Args:
            clerk_user_id: Clerk user identifier

        Returns:
            User model instance or None if not found
        """
        stmt = select(User).where(User.clerk_user_id == clerk_user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.

        Args:
            email: User's email address

        Returns:
            User model instance or None if not found
        """
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        """
        Create new user.

        Args:
            user: User model instance to create

        Returns:
            Created user with assigned ID
        """
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update(self, user: User) -> User:
        """
        Update existing user.

        Args:
            user: User model instance with updates

        Returns:
            Updated user model instance
        """
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def delete(self, user_id: UUID) -> bool:
        """
        Delete user by ID.

        Args:
            user_id: User UUID to delete

        Returns:
            True if user was deleted, False if not found
        """
        user = await self.get_by_id(user_id)
        if user:
            await self.db.delete(user)
            await self.db.commit()
            return True
        return False

    async def list_users(
        self, limit: int = 20, offset: int = 0, active_only: bool = True
    ) -> List[User]:
        """
        List users with pagination.

        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip
            active_only: Whether to return only active users

        Returns:
            List of user model instances
        """
        stmt = select(User)

        if active_only:
            stmt = stmt.where(User.is_active == True)

        stmt = stmt.limit(limit).offset(offset).order_by(User.created_at.desc())

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_user_with_chats(self, user_id: UUID) -> Optional[User]:
        """
        Get user with loaded chat relationships.

        Args:
            user_id: User UUID

        Returns:
            User model with chats loaded, or None if not found
        """
        stmt = select(User).options(selectinload(User.chats)).where(User.id == user_id)

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_last_login(self, user_id: UUID) -> None:
        """
        Update user's last login timestamp.

        Args:
            user_id: User UUID
        """
        from datetime import datetime

        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(
                updated_at=datetime.utcnow(),
                user_metadata=User.user_metadata.op("||")(
                    {"last_login_at": datetime.utcnow().isoformat()}
                ),
            )
        )

        await self.db.execute(stmt)
        await self.db.commit()

    async def count_total_users(self, active_only: bool = True) -> int:
        """
        Count total number of users.

        Args:
            active_only: Whether to count only active users

        Returns:
            Total user count
        """
        from sqlalchemy import func

        stmt = select(func.count(User.id))

        if active_only:
            stmt = stmt.where(User.is_active == True)

        result = await self.db.execute(stmt)
        return result.scalar() or 0
