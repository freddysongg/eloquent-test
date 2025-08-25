"""
Chat repository for database operations with full SQLAlchemy implementation.
"""

import logging
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import and_, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import Chat

logger = logging.getLogger(__name__)


class ChatRepository:
    """Repository for Chat model database operations."""

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize chat repository.

        Args:
            db: Async database session
        """
        self.db = db
        logger.info("Chat repository initialized")

    async def get_by_id(self, chat_id: UUID) -> Optional[Chat]:
        """
        Get chat by ID with messages eagerly loaded.

        Args:
            chat_id: Chat UUID to retrieve

        Returns:
            Chat instance or None if not found
        """
        try:
            stmt = (
                select(Chat)
                .options(selectinload(Chat.messages))
                .where(Chat.id == chat_id)
            )
            result = await self.db.execute(stmt)
            chat = result.scalar_one_or_none()

            logger.info(
                f"Retrieved chat: {chat_id} ({'found' if chat else 'not found'})"
            )
            return chat

        except Exception as e:
            logger.error(f"Failed to get chat by ID {chat_id}: {str(e)}")
            raise

    async def create(self, chat: Chat) -> Chat:
        """
        Create new chat in database.

        Args:
            chat: Chat instance to create

        Returns:
            Created chat with generated ID
        """
        try:
            # Ensure chat has an ID
            if not chat.id:
                chat.id = uuid4()

            self.db.add(chat)
            await self.db.commit()
            await self.db.refresh(chat)

            logger.info(f"Created chat: {chat.id} - '{chat.title}'")
            return chat

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create chat '{chat.title}': {str(e)}")
            raise

    async def list_by_user(
        self, user_id: UUID, limit: int = 50, include_archived: bool = False
    ) -> List[Chat]:
        """
        List chats by user ID with filtering options.

        Args:
            user_id: User UUID to filter by
            limit: Maximum number of chats to return
            include_archived: Whether to include archived chats

        Returns:
            List of user's chats ordered by creation date (newest first)
        """
        try:
            stmt = (
                select(Chat)
                .where(Chat.user_id == user_id)
                .order_by(desc(Chat.is_pinned), desc(Chat.created_at))
                .limit(limit)
            )

            if not include_archived:
                stmt = stmt.where(Chat.is_archived == False)

            result = await self.db.execute(stmt)
            chats = result.scalars().all()

            logger.info(f"Listed {len(chats)} chats for user {user_id}")
            return list(chats)

        except Exception as e:
            logger.error(f"Failed to list chats for user {user_id}: {str(e)}")
            raise

    async def list_by_session(
        self, session_id: str, limit: int = 50, include_archived: bool = False
    ) -> List[Chat]:
        """
        List chats by session ID for anonymous users.

        Args:
            session_id: Session identifier
            limit: Maximum number of chats to return
            include_archived: Whether to include archived chats

        Returns:
            List of session's chats ordered by creation date (newest first)
        """
        try:
            stmt = (
                select(Chat)
                .where(Chat.session_id == session_id)
                .order_by(desc(Chat.is_pinned), desc(Chat.created_at))
                .limit(limit)
            )

            if not include_archived:
                stmt = stmt.where(Chat.is_archived == False)

            result = await self.db.execute(stmt)
            chats = result.scalars().all()

            logger.info(f"Listed {len(chats)} chats for session {session_id}")
            return list(chats)

        except Exception as e:
            logger.error(f"Failed to list chats for session {session_id}: {str(e)}")
            raise

    async def update(self, chat: Chat) -> Chat:
        """
        Update existing chat in database.

        Args:
            chat: Chat instance with updates

        Returns:
            Updated chat instance
        """
        try:
            await self.db.merge(chat)
            await self.db.commit()
            await self.db.refresh(chat)

            logger.info(f"Updated chat: {chat.id}")
            return chat

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update chat {chat.id}: {str(e)}")
            raise

    async def delete(self, chat_id: UUID) -> bool:
        """
        Delete chat and all associated messages.

        Args:
            chat_id: Chat UUID to delete

        Returns:
            True if deleted successfully
        """
        try:
            stmt = select(Chat).where(Chat.id == chat_id)
            result = await self.db.execute(stmt)
            chat = result.scalar_one_or_none()

            if not chat:
                logger.warning(f"Chat not found for deletion: {chat_id}")
                return False

            await self.db.delete(chat)
            await self.db.commit()

            logger.info(f"Deleted chat: {chat_id}")
            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete chat {chat_id}: {str(e)}")
            raise
