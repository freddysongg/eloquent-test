"""
Chat model for conversation management.

Handles chat sessions for both authenticated and anonymous users
with support for metadata and archiving.
"""

from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import Boolean, Column, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class Chat(Base):
    """
    Chat model for conversation sessions.
    
    Supports both authenticated users (via user_id) and anonymous users
    (via session_id) with conversation metadata and archiving capabilities.
    """
    
    __tablename__ = "chats"
    
    # User association (nullable for anonymous users)
    user_id: Optional[UUID] = Column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="Associated user ID for authenticated users"
    )
    
    # Anonymous user session tracking
    session_id: Optional[str] = Column(
        String(255),
        nullable=True,
        index=True,
        doc="Session identifier for anonymous users"
    )
    
    # Chat metadata
    title: str = Column(
        String(255),
        nullable=False,
        default="New Chat",
        doc="Chat conversation title"
    )
    
    description: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Optional chat description or summary"
    )
    
    # Chat status and organization
    is_archived: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        doc="Whether chat is archived (hidden from main list)"
    )
    
    is_pinned: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether chat is pinned to top of list"
    )
    
    # Chat configuration and metadata
    metadata: Dict[str, Any] = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Chat configuration, tags, and additional metadata"
    )
    
    # Relationships
    user = relationship(
        "User",
        back_populates="chats",
        lazy="select"
    )
    
    messages = relationship(
        "Message",
        back_populates="chat",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="Message.created_at"
    )
    
    def __init__(
        self,
        title: str = "New Chat",
        user_id: Optional[UUID] = None,
        session_id: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize chat with title and user/session association.
        
        Args:
            title: Chat conversation title
            user_id: Associated user ID for authenticated users
            session_id: Session ID for anonymous users
            **kwargs: Additional field values
        """
        super().__init__(**kwargs)
        self.title = title
        self.user_id = user_id
        self.session_id = session_id
        
        # Ensure either user_id or session_id is provided
        if not user_id and not session_id:
            raise ValueError("Either user_id or session_id must be provided")
    
    @property
    def is_anonymous(self) -> bool:
        """
        Check if chat belongs to anonymous user.
        
        Returns:
            True if chat is for anonymous user, False otherwise
        """
        return self.user_id is None and self.session_id is not None
    
    @property
    def message_count(self) -> int:
        """
        Get number of messages in chat.
        
        Returns:
            Count of messages in this chat
        """
        return len(self.messages) if self.messages else 0
    
    def generate_title_from_messages(self, max_length: int = 50) -> str:
        """
        Generate chat title from first user message.
        
        Args:
            max_length: Maximum title length
            
        Returns:
            Generated title based on first message content
        """
        if not self.messages:
            return "New Chat"
        
        # Find first user message
        first_user_message = next(
            (msg for msg in self.messages if msg.role == "user"),
            None
        )
        
        if not first_user_message or not first_user_message.content:
            return "New Chat"
        
        # Clean and truncate content for title
        content = first_user_message.content.strip()
        if len(content) <= max_length:
            return content
        else:
            return content[:max_length-3] + "..."
    
    def update_title_from_content(self) -> None:
        """Update chat title based on message content if still default."""
        if self.title in ["New Chat", ""]:
            self.title = self.generate_title_from_messages()
    
    def archive(self) -> None:
        """Archive the chat (hide from main list)."""
        self.is_archived = True
    
    def unarchive(self) -> None:
        """Unarchive the chat (show in main list)."""
        self.is_archived = False
    
    def pin(self) -> None:
        """Pin chat to top of list."""
        self.is_pinned = True
    
    def unpin(self) -> None:
        """Unpin chat from top of list."""
        self.is_pinned = False
    
    def add_tag(self, tag: str) -> None:
        """
        Add tag to chat metadata.
        
        Args:
            tag: Tag string to add
        """
        if self.metadata is None:
            self.metadata = {}
        
        tags = self.metadata.get("tags", [])
        if tag not in tags:
            tags.append(tag)
            self.metadata["tags"] = tags
    
    def remove_tag(self, tag: str) -> None:
        """
        Remove tag from chat metadata.
        
        Args:
            tag: Tag string to remove
        """
        if self.metadata and "tags" in self.metadata:
            tags = self.metadata["tags"]
            if tag in tags:
                tags.remove(tag)
                self.metadata["tags"] = tags
    
    def get_tags(self) -> list[str]:
        """
        Get list of chat tags.
        
        Returns:
            List of tag strings
        """
        return self.metadata.get("tags", []) if self.metadata else []
    
    def to_dict(self, exclude: Optional[set] = None, include_messages: bool = False) -> Dict[str, Any]:
        """
        Convert chat to dictionary with additional computed fields.
        
        Args:
            exclude: Fields to exclude from output
            include_messages: Whether to include messages in output
            
        Returns:
            Dictionary representation with message_count and other computed fields
        """
        data = super().to_dict(exclude=exclude)
        data.update({
            "is_anonymous": self.is_anonymous,
            "message_count": self.message_count,
            "tags": self.get_tags()
        })
        
        if include_messages and self.messages:
            data["messages"] = [msg.to_dict() for msg in self.messages]
        
        return data
    
    def __repr__(self) -> str:
        """String representation of chat."""
        user_info = f"user_id={self.user_id}" if self.user_id else f"session_id={self.session_id}"
        return f"<Chat(id={self.id}, {user_info}, title='{self.title}')>"