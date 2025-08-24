"""
User model with Clerk authentication integration.

Handles user data synchronization with Clerk Auth service
and manages user preferences and metadata.
"""

from typing import Any, Dict, Optional

from sqlalchemy import Boolean, Column, JSON, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base


class User(Base):
    """
    User model with Clerk integration.
    
    Stores user data synchronized from Clerk authentication service
    with support for preferences and metadata storage.
    """
    
    __tablename__ = "users"
    
    # Clerk integration fields
    clerk_user_id: str = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="Clerk user identifier for authentication"
    )
    
    email: Optional[str] = Column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
        doc="Primary email address from Clerk"
    )
    
    # User profile fields
    first_name: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="User's first name"
    )
    
    last_name: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="User's last name"
    )
    
    display_name: Optional[str] = Column(
        String(200),
        nullable=True,
        doc="User's preferred display name"
    )
    
    avatar_url: Optional[str] = Column(
        Text,
        nullable=True,
        doc="URL to user's profile avatar"
    )
    
    # Account status
    is_active: bool = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        doc="Whether user account is active"
    )
    
    is_verified: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether user email is verified"
    )
    
    # User preferences and metadata
    preferences: Dict[str, Any] = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="User preferences and settings"
    )
    
    metadata: Dict[str, Any] = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Additional user metadata and custom fields"
    )
    
    # Relationships
    chats = relationship(
        "Chat",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    def __init__(
        self,
        clerk_user_id: str,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize user with required fields.
        
        Args:
            clerk_user_id: Clerk user identifier
            email: User's primary email address
            first_name: User's first name
            last_name: User's last name
            **kwargs: Additional field values
        """
        super().__init__(**kwargs)
        self.clerk_user_id = clerk_user_id
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
    
    @property
    def full_name(self) -> str:
        """
        Get user's full name.
        
        Returns:
            Formatted full name or email if name not available
        """
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.display_name:
            return self.display_name
        elif self.email:
            return self.email.split("@")[0]
        else:
            return f"User {self.clerk_user_id[:8]}"
    
    def update_from_clerk(self, clerk_data: Dict[str, Any]) -> None:
        """
        Update user data from Clerk webhook or API response.
        
        Args:
            clerk_data: User data from Clerk API
        """
        # Update basic profile fields
        self.first_name = clerk_data.get("first_name")
        self.last_name = clerk_data.get("last_name")
        
        # Update email from primary email address
        email_addresses = clerk_data.get("email_addresses", [])
        primary_email = next(
            (email["email_address"] for email in email_addresses 
             if email.get("primary_email_address_id")),
            None
        )
        if primary_email:
            self.email = primary_email
        
        # Update verification status
        self.is_verified = any(
            email.get("verification", {}).get("status") == "verified"
            for email in email_addresses
        )
        
        # Update avatar URL
        self.avatar_url = clerk_data.get("profile_image_url")
        
        # Store additional Clerk metadata
        self.metadata.update({
            "clerk_created_at": clerk_data.get("created_at"),
            "clerk_updated_at": clerk_data.get("updated_at"),
            "last_sign_in_at": clerk_data.get("last_sign_in_at"),
        })
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """
        Get user preference value.
        
        Args:
            key: Preference key name
            default: Default value if preference not set
            
        Returns:
            Preference value or default
        """
        return self.preferences.get(key, default)
    
    def set_preference(self, key: str, value: Any) -> None:
        """
        Set user preference value.
        
        Args:
            key: Preference key name
            value: Preference value to set
        """
        if self.preferences is None:
            self.preferences = {}
        self.preferences[key] = value
    
    def to_dict(self, exclude: Optional[set] = None) -> Dict[str, Any]:
        """
        Convert user to dictionary with additional computed fields.
        
        Args:
            exclude: Fields to exclude from output
            
        Returns:
            Dictionary representation including full_name
        """
        data = super().to_dict(exclude=exclude)
        data["full_name"] = self.full_name
        return data
    
    def __repr__(self) -> str:
        """String representation of user."""
        return f"<User(id={self.id}, clerk_id={self.clerk_user_id}, email={self.email})>"