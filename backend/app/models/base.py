"""
Base model class with common fields and utilities.

Provides UUID primary keys, timestamps, and database session management
for all application models.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, Optional

from sqlalchemy import DateTime, MetaData
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import Mapped, mapped_column

if TYPE_CHECKING:
    from sqlalchemy.sql.schema import Table

from app.core.config import settings

# Create async database engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True,
    autocommit=False,
)


@as_declarative()
class Base:
    """Base class for all database models."""

    # Add type hints for SQLAlchemy attributes
    __name__: str
    __table__: "Table"
    metadata: MetaData

    # Modern SQLAlchemy 2.0 typing
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        doc="Primary key UUID",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
        doc="Timestamp when record was created",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        index=True,
        doc="Timestamp when record was last updated",
    )

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        return cls.__name__.lower() + "s"

    def to_dict(self, exclude: Optional[set] = None) -> Dict[str, Any]:
        """
        Convert model to dictionary representation.

        Args:
            exclude: Set of field names to exclude from output

        Returns:
            Dictionary representation of model
        """
        exclude = exclude or set()
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
            if column.name not in exclude
        }

    def update_fields(self, **kwargs: Any) -> None:
        """
        Update multiple model fields at once.

        Args:
            **kwargs: Field names and values to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

        # Automatically update the updated_at timestamp
        self.updated_at = datetime.utcnow()

    def __repr__(self) -> str:
        """String representation of model."""
        return f"<{self.__class__.__name__}(id={self.id})>"


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get async database session for dependency injection.

    Yields:
        Database session instance
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        # Import all models to ensure they're registered
        from app.models.chat import Chat  # noqa: F401
        from app.models.message import Message  # noqa: F401
        from app.models.user import User  # noqa: F401

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
