"""
Application configuration management using Pydantic settings.

Handles environment variables, validation, and application settings
with proper type hints and secure defaults.
"""

import secrets
from typing import List, Optional, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )

    # Application Settings
    APP_NAME: str = "Eloquent AI Backend"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = False

    # Database Configuration
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://eloquent:eloquent_password@localhost:5432/eloquentai_dev",  # pragma: allowlist secret
        description="PostgreSQL database URL with asyncpg driver",
    )
    DATABASE_ECHO: bool = False
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0

    # Authentication & Security
    SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="Secret key for JWT token signing",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Clerk Authentication
    CLERK_PUBLISHABLE_KEY: str = Field(
        default="pk_test_development",
        description="Clerk publishable key for frontend authentication",
    )
    CLERK_SECRET_KEY: str = Field(
        default="sk_test_development",
        description="Clerk secret key for backend verification",
    )
    CLERK_JWT_TEMPLATE: str = "eloquent-ai"

    # AI Services
    ANTHROPIC_API_KEY: str = Field(
        default="sk-ant-development",
        description="Anthropic API key for Claude integration",
    )
    CLAUDE_MODEL: str = "claude-3-5-sonnet-20241022"
    CLAUDE_MAX_TOKENS: int = 4096

    # Pinecone Configuration
    PINECONE_API_KEY: str = Field(
        default="development-key", description="Pinecone API key for vector database"
    )
    PINECONE_ENVIRONMENT: str = "us-east-1"
    PINECONE_INDEX_NAME: str = "ai-powered-chatbot-challenge"
    PINECONE_INDEX_HOST: str = Field(
        default="https://ai-powered-chatbot-challenge-omkb0qa.svc.aped-4627-b74a.pinecone.io",
        description="Pinecone index host URL",
    )

    # Embedding Model Configuration
    EMBEDDING_MODEL: str = "llama-text-embed-v2"
    EMBEDDING_DIMENSIONS: int = 1024
    EMBEDDING_CACHE_TTL_SECONDS: int = 3600  # 1 hour cache
    EMBEDDING_REQUEST_TIMEOUT_SECONDS: int = 10

    # OpenAI Configuration (fallback for embeddings)
    OPENAI_API_KEY: Optional[str] = Field(
        default=None, description="OpenAI API key for embedding fallback"
    )
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-large"

    # Rate Limiting
    RATE_LIMIT_GLOBAL_REQUESTS_PER_MINUTE: int = 1000
    RATE_LIMIT_AUTHENTICATED_REQUESTS_PER_MINUTE: int = 100
    RATE_LIMIT_ANONYMOUS_REQUESTS_PER_MINUTE: int = 20
    RATE_LIMIT_LLM_REQUESTS_PER_MINUTE: int = 10

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: str = "logs/app.log"

    # CORS Settings
    CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",  # Local development
            "https://eloquent-test.vercel.app",  # Production frontend
        ],
        description="List of allowed CORS origins",
    )
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
    )
    CORS_ALLOW_HEADERS: List[str] = Field(default=["*"])

    # Monitoring & Observability
    SENTRY_DSN: Optional[str] = None
    PROMETHEUS_METRICS_ENABLED: bool = True
    HEALTH_CHECK_ENABLED: bool = True

    # Celery Configuration
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # WebSocket Configuration
    WEBSOCKET_HEARTBEAT_INTERVAL: int = 30
    WEBSOCKET_MAX_CONNECTIONS: int = 1000

    # Performance Settings
    REQUEST_TIMEOUT_SECONDS: int = 30
    RESPONSE_TIMEOUT_SECONDS: int = 60
    MAX_CHAT_HISTORY_LENGTH: int = 50

    @field_validator("CORS_ORIGINS", mode="before")
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        elif isinstance(v, list):
            return v
        raise ValueError("CORS_ORIGINS must be a string or list")

    @field_validator("DATABASE_URL", mode="before")
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format with development fallback."""
        if not v or v in ["...", "required"]:
            # Return development default if not provided
            return "postgresql+asyncpg://eloquent:eloquent_password@localhost:5432/eloquentai_dev"  # pragma: allowlist secret

        if not v.startswith(("postgresql://", "postgresql+asyncpg://")):
            raise ValueError("DATABASE_URL must use PostgreSQL with asyncpg driver")
        return v

    @field_validator("REDIS_URL", mode="before")
    def validate_redis_url(cls, v: str) -> str:
        """Validate Redis URL format with development fallback."""
        if not v or not v.startswith("redis://"):
            # Return development default if not provided or invalid
            return "redis://localhost:6379/0"
        return v

    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL for migrations."""
        return self.DATABASE_URL.replace("+asyncpg", "")


# Global settings instance
settings = Settings()  # type: ignore[call-arg]


def get_settings() -> Settings:
    """Get application settings instance for dependency injection."""
    return settings
