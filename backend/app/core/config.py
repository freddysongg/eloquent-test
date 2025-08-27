"""
Application configuration management using Pydantic settings.

Handles environment variables, validation, and application settings
with proper type hints and secure defaults.
"""

import os
import secrets
from typing import Annotated, List, Optional, Union

from pydantic import Field, PlainValidator, field_validator
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
    REDIS_SSL: bool = Field(
        default=False,
        description="Enable SSL/TLS for Redis connections (required for ElastiCache in-transit encryption)",
    )
    REDIS_CLUSTER_MODE: bool = Field(
        default=False, description="Enable Redis cluster mode for ElastiCache cluster"
    )

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
    CLERK_WEBHOOK_SECRET: Optional[str] = Field(
        default=None,
        description="Clerk webhook signing secret for secure webhook validation",
    )

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
    @staticmethod
    def parse_cors_origins(v: Union[str, List[str]]) -> List[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            # Try to parse as JSON first
            try:
                import json

                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass
            # Fall back to comma-separated parsing
            return [origin.strip() for origin in v.split(",")]
        elif isinstance(v, list):
            return v
        raise ValueError("CORS_ORIGINS must be a string or list")

    CORS_ORIGINS: Annotated[List[str], PlainValidator(parse_cors_origins)] = Field(
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

    # AWS Configuration
    AWS_REGION: str = Field(
        default="us-east-1", description="AWS region for services like Secrets Manager"
    )
    AWS_SECRETS_ENABLED: bool = Field(
        default=True, description="Enable AWS Secrets Manager integration"
    )

    # Secrets Manager Configuration
    APP_SECRETS_NAME: Optional[str] = Field(
        default=None,
        description="AWS Secrets Manager secret name for application credentials",
    )
    JWT_SECRETS_NAME: Optional[str] = Field(
        default=None, description="AWS Secrets Manager secret name for JWT secrets"
    )

    @field_validator("DATABASE_URL", mode="before")
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format with development fallback."""
        if not v or v in ["...", "required"]:
            # Return development default if not provided
            return "postgresql+asyncpg://eloquent:eloquent_password@localhost:5432/eloquentai_dev"  # pragma: allowlist secret

        # Ensure async driver is used
        if v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
            # Convert to async format
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
            print(f"🔄 Auto-converted DATABASE_URL to use asyncpg driver")
        elif not v.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "DATABASE_URL must use PostgreSQL with asyncpg driver format: postgresql+asyncpg://"
            )

        # Additional validation: ensure URL structure is correct
        if "://" not in v or v.count("@") != 1 or v.count("/") < 3:
            raise ValueError(
                "DATABASE_URL format is invalid. Expected: postgresql+asyncpg://user:pass@host:port/database"  # pragma: allowlist secret
            )

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

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() == "production"

    def is_aws_environment(self) -> bool:
        """Check if running in AWS environment (ECS/Fargate)."""
        # Check for ECS metadata endpoint or AWS environment variables
        return (
            os.getenv("AWS_EXECUTION_ENV") is not None
            or os.getenv("ECS_CONTAINER_METADATA_URI") is not None
            or os.getenv("ECS_CONTAINER_METADATA_URI_V4") is not None
            or self.is_production()
        )

    async def load_aws_secrets(self) -> None:
        """Load secrets from AWS Secrets Manager if enabled and in AWS environment."""
        if not self.AWS_SECRETS_ENABLED or not self.is_aws_environment():
            return

        try:
            from app.integrations.secrets_manager import get_secrets_client

            secrets_client = get_secrets_client()

            # Load application credentials if configured
            if self.APP_SECRETS_NAME:
                app_secrets = await secrets_client.get_secret(self.APP_SECRETS_NAME)

                # Update configuration with secrets
                if "database_url" in app_secrets:
                    self.DATABASE_URL = app_secrets["database_url"]
                if "anthropic_api_key" in app_secrets:
                    self.ANTHROPIC_API_KEY = app_secrets["anthropic_api_key"]
                if "pinecone_api_key" in app_secrets:
                    self.PINECONE_API_KEY = app_secrets["pinecone_api_key"]
                if "clerk_secret_key" in app_secrets:
                    self.CLERK_SECRET_KEY = app_secrets["clerk_secret_key"]
                if "redis_url" in app_secrets:
                    self.REDIS_URL = app_secrets["redis_url"]

            # Load JWT secrets if configured
            if self.JWT_SECRETS_NAME:
                jwt_secrets = await secrets_client.get_secret(self.JWT_SECRETS_NAME)
                if "password" in jwt_secrets:
                    self.SECRET_KEY = jwt_secrets["password"]

        except Exception as e:
            # Log error but don't fail startup in case of secrets issues
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to load AWS secrets: {str(e)}")

            # In production, this might be a critical error
            if self.is_production():
                logger.critical("AWS Secrets Manager failed in production environment")
                # In a real production setup, you might want to raise here
                # raise e


# Global settings instance
settings = Settings()  # type: ignore[call-arg]


def get_settings() -> Settings:
    """Get application settings instance for dependency injection."""
    return settings
