"""
Message repository for database operations.

Handles CRUD operations for messages with support for RAG metadata,
chat history retrieval, and sequence number management.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, asc, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message, MessageRole

logger = logging.getLogger(__name__)


class MessageRepository:
    """Repository for Message model database operations."""

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize message repository.

        Args:
            db: Async database session
        """
        self.db = db

    async def create(
        self,
        chat_id: UUID,
        role: MessageRole,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> Message:
        """
        Create new message with auto-incremented sequence number.

        Args:
            chat_id: Chat conversation ID
            role: Message role (user, assistant, system)
            content: Message text content
            metadata: Optional message metadata
            correlation_id: Request correlation ID

        Returns:
            Created message instance

        Raises:
            ValueError: If content is empty or chat_id is invalid
        """
        if not content.strip():
            raise ValueError("Message content cannot be empty")

        try:
            # Get next sequence number for this chat
            sequence_result = await self.db.execute(
                select(Message.sequence_number)
                .where(Message.chat_id == chat_id)
                .order_by(desc(Message.sequence_number))
                .limit(1)
            )

            last_sequence = sequence_result.scalar()
            next_sequence = (last_sequence + 1) if last_sequence is not None else 1

            # Create message with sequence number
            message = Message(
                chat_id=chat_id,
                role=role,
                content=content.strip(),
                sequence_number=next_sequence,
                metadata=metadata or {},
            )

            self.db.add(message)
            await self.db.commit()
            await self.db.refresh(message)

            logger.info(
                f"Created message",
                extra={
                    "correlation_id": correlation_id,
                    "message_id": str(message.id),
                    "chat_id": str(chat_id),
                    "role": role.value,
                    "sequence_number": next_sequence,
                    "content_length": len(content),
                    "has_metadata": bool(metadata),
                },
            )

            return message

        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Failed to create message: {str(e)}",
                extra={
                    "correlation_id": correlation_id,
                    "chat_id": str(chat_id),
                    "role": role.value,
                },
            )
            raise

    async def create_with_rag_metadata(
        self,
        chat_id: UUID,
        role: MessageRole,
        content: str,
        retrieved_docs: List[Dict[str, Any]],
        retrieval_query: str,
        rag_metadata: Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> Message:
        """
        Create message with RAG context metadata.

        Args:
            chat_id: Chat conversation ID
            role: Message role (typically assistant for RAG responses)
            content: Message text content
            retrieved_docs: List of retrieved document chunks
            retrieval_query: Query used for RAG retrieval
            rag_metadata: Additional RAG metadata (search method, confidence, etc.)
            correlation_id: Request correlation ID

        Returns:
            Created message with RAG metadata
        """
        # Build complete metadata with RAG context
        metadata = rag_metadata or {}

        # Set RAG context
        metadata["rag_context"] = {
            "retrieved_docs": retrieved_docs,
            "retrieval_query": retrieval_query,
            "doc_count": len(retrieved_docs),
            "relevance_scores": [
                doc.get("enhanced_score", doc.get("score", 0)) for doc in retrieved_docs
            ],
        }

        # Add search method info if available
        if retrieved_docs and any(doc.get("hybrid_score") for doc in retrieved_docs):
            metadata["rag_context"]["search_method"] = "hybrid"
            metadata["rag_context"]["hybrid_scores"] = [
                doc.get("hybrid_score", 0) for doc in retrieved_docs
            ]
            metadata["rag_context"]["confidence"] = sum(
                doc.get("confidence", 0) for doc in retrieved_docs
            ) / len(retrieved_docs)
        else:
            metadata["rag_context"]["search_method"] = "vector_only"

        # Add source attribution
        sources = []
        for doc in retrieved_docs:
            source_attr = doc.get("source_attribution", {})
            if source_attr:
                sources.append(
                    {
                        "category": source_attr.get("category", "unknown"),
                        "source": source_attr.get("source", "unknown"),
                        "title": source_attr.get("title", ""),
                    }
                )

        if sources:
            metadata["rag_context"]["sources"] = sources

        return await self.create(
            chat_id=chat_id,
            role=role,
            content=content,
            metadata=metadata,
            correlation_id=correlation_id,
        )

    async def get_by_id(self, message_id: UUID) -> Optional[Message]:
        """
        Get message by ID.

        Args:
            message_id: Message ID

        Returns:
            Message instance or None if not found
        """
        result = await self.db.execute(select(Message).where(Message.id == message_id))

        return result.scalar_one_or_none()

    async def get_chat_history(
        self,
        chat_id: UUID,
        limit: int = 50,
        offset: int = 0,
        include_rag_metadata: bool = False,
        correlation_id: str = "",
    ) -> List[Message]:
        """
        Get chat message history ordered by sequence number.

        Args:
            chat_id: Chat conversation ID
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            include_rag_metadata: Whether to include full RAG metadata
            correlation_id: Request correlation ID

        Returns:
            List of messages ordered by sequence number
        """
        try:
            result = await self.db.execute(
                select(Message)
                .where(Message.chat_id == chat_id)
                .order_by(asc(Message.sequence_number))
                .offset(offset)
                .limit(limit)
            )

            messages = result.scalars().all()

            logger.info(
                f"Retrieved chat history",
                extra={
                    "correlation_id": correlation_id,
                    "chat_id": str(chat_id),
                    "message_count": len(messages),
                    "limit": limit,
                    "offset": offset,
                },
            )

            return list(messages)

        except Exception as e:
            logger.error(
                f"Failed to get chat history: {str(e)}",
                extra={"correlation_id": correlation_id, "chat_id": str(chat_id)},
            )
            return []

    async def get_recent_context(
        self,
        chat_id: UUID,
        max_messages: int = 10,
        max_tokens: int = 4000,
        correlation_id: str = "",
    ) -> List[Dict[str, str]]:
        """
        Get recent conversation context for AI generation.

        Args:
            chat_id: Chat conversation ID
            max_messages: Maximum number of messages to include
            max_tokens: Maximum token count for context (approximate)
            correlation_id: Request correlation ID

        Returns:
            List of formatted messages for AI context
        """
        try:
            # Get recent messages excluding system messages
            result = await self.db.execute(
                select(Message)
                .where(
                    and_(Message.chat_id == chat_id, Message.role != MessageRole.SYSTEM)
                )
                .order_by(desc(Message.sequence_number))
                .limit(max_messages)
            )

            messages = list(reversed(result.scalars().all()))

            # Convert to AI-friendly format with token awareness
            context_messages = []
            current_tokens = 0

            for message in messages:
                # Estimate tokens (rough approximation: 1 token ≈ 4 characters)
                estimated_tokens = len(message.content) // 4

                if current_tokens + estimated_tokens > max_tokens:
                    break

                context_messages.append(
                    {"role": message.role.value, "content": message.content}
                )

                current_tokens += estimated_tokens

            logger.info(
                f"Built conversation context",
                extra={
                    "correlation_id": correlation_id,
                    "chat_id": str(chat_id),
                    "context_messages": len(context_messages),
                    "estimated_tokens": current_tokens,
                },
            )

            return context_messages

        except Exception as e:
            logger.error(
                f"Failed to get recent context: {str(e)}",
                extra={"correlation_id": correlation_id, "chat_id": str(chat_id)},
            )
            return []

    async def get_messages_with_rag_context(
        self, chat_id: UUID, limit: int = 20, correlation_id: str = ""
    ) -> List[Message]:
        """
        Get messages that include RAG context information.

        Args:
            chat_id: Chat conversation ID
            limit: Maximum number of messages to return
            correlation_id: Request correlation ID

        Returns:
            List of messages with RAG context
        """
        try:
            result = await self.db.execute(
                select(Message)
                .where(
                    and_(
                        Message.chat_id == chat_id,
                        Message.message_metadata.op("?")(["rag_context"]),
                    )
                )
                .order_by(desc(Message.sequence_number))
                .limit(limit)
            )

            messages = result.scalars().all()

            logger.info(
                f"Retrieved messages with RAG context",
                extra={
                    "correlation_id": correlation_id,
                    "chat_id": str(chat_id),
                    "message_count": len(messages),
                },
            )

            return list(messages)

        except Exception as e:
            logger.error(
                f"Failed to get messages with RAG context: {str(e)}",
                extra={"correlation_id": correlation_id, "chat_id": str(chat_id)},
            )
            return []

    async def update_metadata(
        self,
        message_id: UUID,
        metadata_updates: Dict[str, Any],
        correlation_id: str = "",
    ) -> bool:
        """
        Update message metadata.

        Args:
            message_id: Message ID
            metadata_updates: Metadata fields to update
            correlation_id: Request correlation ID

        Returns:
            True if update successful, False otherwise
        """
        try:
            message = await self.get_by_id(message_id)
            if not message:
                return False

            # Update metadata
            if message.message_metadata is None:
                message.message_metadata = {}

            message.message_metadata.update(metadata_updates)

            await self.db.commit()

            logger.info(
                f"Updated message metadata",
                extra={
                    "correlation_id": correlation_id,
                    "message_id": str(message_id),
                    "updated_fields": list(metadata_updates.keys()),
                },
            )

            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Failed to update message metadata: {str(e)}",
                extra={"correlation_id": correlation_id, "message_id": str(message_id)},
            )
            return False

    async def delete_by_chat_id(self, chat_id: UUID) -> int:
        """
        Delete all messages for a chat (cascade delete).

        Args:
            chat_id: Chat conversation ID

        Returns:
            Number of deleted messages
        """
        try:
            result = await self.db.execute(
                select(Message).where(Message.chat_id == chat_id)
            )

            messages = result.scalars().all()
            message_count = len(messages)

            for message in messages:
                await self.db.delete(message)

            await self.db.commit()

            logger.info(f"Deleted {message_count} messages for chat {chat_id}")

            return message_count

        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Failed to delete messages: {str(e)}", extra={"chat_id": str(chat_id)}
            )
            return 0
