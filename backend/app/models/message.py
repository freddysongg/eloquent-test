"""
Message model for chat conversation content.

Handles individual messages within chat conversations with support
for different message types, metadata, and RAG context tracking.
"""

from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import JSON
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class MessageRole(str, Enum):
    """Message role enumeration for conversation participants."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(Base):
    """
    Message model for chat conversation content.

    Stores individual messages with role identification, content,
    and metadata including token counts and RAG context information.
    """

    __tablename__ = "messages"

    # Chat association
    chat_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Associated chat conversation ID",
    )

    # Message content and identification
    role: Mapped[MessageRole] = mapped_column(
        SQLEnum(MessageRole),
        nullable=False,
        index=True,
        doc="Message role: user, assistant, or system",
    )

    content: Mapped[str] = mapped_column(
        Text, nullable=False, doc="Message text content"
    )

    # Message ordering within chat
    sequence_number: Mapped[int] = mapped_column(
        Integer, nullable=False, doc="Sequential message number within chat"
    )

    # Message metadata and tracking
    message_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
        doc="Message metadata including tokens, model info, and RAG context",
    )

    # Relationships
    chat = relationship("Chat", back_populates="messages", lazy="select")

    def __init__(
        self,
        chat_id: UUID,
        role: MessageRole,
        content: str,
        sequence_number: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize message with required fields.

        Args:
            chat_id: Associated chat ID
            role: Message role (user, assistant, system)
            content: Message text content
            sequence_number: Sequential number within chat
            **kwargs: Additional field values
        """
        super().__init__(**kwargs)
        self.chat_id = chat_id
        self.role = role
        self.content = content
        self.sequence_number = sequence_number or 0

    @property
    def token_count(self) -> Optional[int]:
        """
        Get message token count from metadata.

        Returns:
            Token count if available, None otherwise
        """
        return (
            self.message_metadata.get("token_count") if self.message_metadata else None
        )

    @property
    def model_used(self) -> Optional[str]:
        """
        Get AI model used for generation from metadata.

        Returns:
            Model name if available, None otherwise
        """
        return self.message_metadata.get("model") if self.message_metadata else None

    @property
    def has_rag_context(self) -> bool:
        """
        Check if message includes RAG context information.

        Returns:
            True if RAG context is available, False otherwise
        """
        return bool(self.message_metadata and self.message_metadata.get("rag_context"))

    def set_token_count(self, count: int) -> None:
        """
        Set message token count in metadata.

        Args:
            count: Number of tokens in message
        """
        if self.message_metadata is None:
            self.message_metadata = {}
        self.message_metadata["token_count"] = count

    def set_model_info(self, model: str, **model_params: Any) -> None:
        """
        Set AI model information in metadata.

        Args:
            model: Model name/identifier
            **model_params: Additional model parameters
        """
        if self.message_metadata is None:
            self.message_metadata = {}

        self.message_metadata.update({"model": model, "model_params": model_params})

    def set_rag_context(
        self,
        retrieved_docs: list[Dict[str, Any]],
        retrieval_query: str,
        relevance_scores: Optional[list[float]] = None,
    ) -> None:
        """
        Set RAG context information in metadata.

        Args:
            retrieved_docs: List of retrieved document chunks
            retrieval_query: Query used for retrieval
            relevance_scores: Optional relevance scores for documents
        """
        if self.message_metadata is None:
            self.message_metadata = {}

        self.message_metadata["rag_context"] = {
            "retrieved_docs": retrieved_docs,
            "retrieval_query": retrieval_query,
            "relevance_scores": relevance_scores,
            "doc_count": len(retrieved_docs),
        }

    def set_streaming_info(
        self,
        stream_id: str,
        total_chunks: Optional[int] = None,
        completion_time: Optional[float] = None,
    ) -> None:
        """
        Set streaming response information in metadata.

        Args:
            stream_id: Unique streaming session identifier
            total_chunks: Total number of response chunks
            completion_time: Total streaming completion time in seconds
        """
        if self.message_metadata is None:
            self.message_metadata = {}

        self.message_metadata["streaming"] = {
            "stream_id": stream_id,
            "total_chunks": total_chunks,
            "completion_time": completion_time,
        }

    def get_rag_documents(self) -> list[Dict[str, Any]]:
        """
        Get retrieved RAG documents from metadata.

        Returns:
            List of retrieved documents or empty list
        """
        rag_context = (
            self.message_metadata.get("rag_context", {})
            if self.message_metadata
            else {}
        )
        return rag_context.get("retrieved_docs", [])

    def get_relevance_scores(self) -> list[float]:
        """
        Get document relevance scores from metadata.

        Returns:
            List of relevance scores or empty list
        """
        rag_context = (
            self.message_metadata.get("rag_context", {})
            if self.message_metadata
            else {}
        )
        return rag_context.get("relevance_scores", [])

    def is_user_message(self) -> bool:
        """
        Check if message is from user.

        Returns:
            True if message role is user
        """
        return self.role == MessageRole.USER

    def is_assistant_message(self) -> bool:
        """
        Check if message is from assistant.

        Returns:
            True if message role is assistant
        """
        return self.role == MessageRole.ASSISTANT

    def is_system_message(self) -> bool:
        """
        Check if message is system message.

        Returns:
            True if message role is system
        """
        return self.role == MessageRole.SYSTEM

    def truncate_content(self, max_length: int = 100) -> str:
        """
        Get truncated message content for previews.

        Args:
            max_length: Maximum content length

        Returns:
            Truncated content with ellipsis if needed
        """
        if len(self.content) <= max_length:
            return self.content
        else:
            return self.content[: max_length - 3] + "..."

    def to_dict(
        self, exclude: Optional[set] = None, include_rag_context: bool = False
    ) -> Dict[str, Any]:
        """
        Convert message to dictionary with additional computed fields.

        Args:
            exclude: Fields to exclude from output
            include_rag_context: Whether to include full RAG context

        Returns:
            Dictionary representation with computed fields
        """
        data = super().to_dict(exclude=exclude)
        data.update(
            {
                "token_count": self.token_count,
                "model_used": self.model_used,
                "has_rag_context": self.has_rag_context,
                "content_preview": self.truncate_content(),
            }
        )

        if include_rag_context and self.has_rag_context:
            data["rag_context"] = self.message_metadata.get("rag_context")

        return data

    def __repr__(self) -> str:
        """String representation of message."""
        content_preview = self.truncate_content(50)
        return f"<Message(id={self.id}, chat_id={self.chat_id}, role={self.role.value}, content='{content_preview}')>"
