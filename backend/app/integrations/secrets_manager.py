"""
AWS Secrets Manager client for secure credential management.

Handles fetching secrets from AWS Secrets Manager with caching,
error handling, and graceful fallback for development environments.
"""

import json
import logging
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings
from app.core.exceptions import ExternalServiceException

logger = logging.getLogger(__name__)


class SecretsManagerClient:
    """AWS Secrets Manager client with caching and graceful fallback."""

    def __init__(self) -> None:
        """Initialize Secrets Manager client with region configuration."""
        self._cache: Dict[str, Any] = {}
        self._client: Optional[Any] = None
        self._mock_mode = False

        try:
            # Initialize AWS Secrets Manager client
            self._client = boto3.client(
                "secretsmanager",
                region_name=getattr(settings, "AWS_REGION", "us-east-1"),
            )
            logger.info("AWS Secrets Manager client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize AWS Secrets Manager client: {str(e)}")

            # In development mode, fall back to environment variables
            if settings.ENVIRONMENT == "development":
                logger.warning("Falling back to environment variables for development")
                self._mock_mode = True
                self._client = None
            else:
                raise ExternalServiceException(
                    "AWS Secrets Manager", f"Client initialization failed: {str(e)}"
                )

    async def get_secret(
        self, secret_name: str, correlation_id: str = ""
    ) -> Dict[str, Any]:
        """
        Retrieve secret from AWS Secrets Manager with caching.

        Args:
            secret_name: Name or ARN of the secret
            correlation_id: Request correlation ID for tracking

        Returns:
            Dictionary containing secret key-value pairs

        Raises:
            ExternalServiceException: If secret retrieval fails
        """
        # Check cache first
        if secret_name in self._cache:
            logger.debug(
                f"Secret '{secret_name}' retrieved from cache",
                extra={"correlation_id": correlation_id},
            )
            return self._cache[secret_name]

        if self._mock_mode:
            # In development, return environment variable-based mock
            mock_secret = self._get_mock_secret(secret_name)
            self._cache[secret_name] = mock_secret
            logger.debug(
                f"Secret '{secret_name}' retrieved from mock (development mode)",
                extra={"correlation_id": correlation_id},
            )
            return mock_secret

        try:
            if self._client is None:
                raise ExternalServiceException(
                    "AWS Secrets Manager", "Client not initialized"
                )

            response = self._client.get_secret_value(SecretId=secret_name)

            # Parse secret string as JSON
            secret_data = json.loads(response["SecretString"])

            # Cache the secret for future requests
            self._cache[secret_name] = secret_data

            logger.info(
                f"Secret '{secret_name}' retrieved from AWS Secrets Manager",
                extra={
                    "correlation_id": correlation_id,
                    "secret_keys": (
                        list(secret_data.keys())
                        if isinstance(secret_data, dict)
                        else []
                    ),
                },
            )

            return secret_data

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]

            logger.error(
                f"AWS Secrets Manager error for '{secret_name}': {error_code} - {error_message}",
                extra={"correlation_id": correlation_id},
            )

            raise ExternalServiceException(
                "AWS Secrets Manager",
                f"Failed to retrieve secret '{secret_name}': {error_code} - {error_message}",
                correlation_id=correlation_id,
            )

        except (BotoCoreError, json.JSONDecodeError, KeyError) as e:
            logger.error(
                f"Failed to retrieve secret '{secret_name}': {str(e)}",
                extra={"correlation_id": correlation_id},
            )

            raise ExternalServiceException(
                "AWS Secrets Manager",
                f"Secret retrieval failed: {str(e)}",
                correlation_id=correlation_id,
            )

    async def get_secret_value(
        self, secret_name: str, key: str, correlation_id: str = ""
    ) -> Optional[str]:
        """
        Get specific value from a secret.

        Args:
            secret_name: Name or ARN of the secret
            key: Key within the secret JSON
            correlation_id: Request correlation ID for tracking

        Returns:
            Secret value as string or None if not found
        """
        try:
            secret_data = await self.get_secret(secret_name, correlation_id)

            if isinstance(secret_data, dict):
                value = secret_data.get(key)
                if value is not None:
                    logger.debug(
                        f"Secret key '{key}' retrieved from '{secret_name}'",
                        extra={"correlation_id": correlation_id},
                    )
                    return str(value)

            logger.warning(
                f"Secret key '{key}' not found in '{secret_name}'",
                extra={"correlation_id": correlation_id},
            )
            return None

        except Exception as e:
            logger.error(
                f"Failed to get secret value '{key}' from '{secret_name}': {str(e)}",
                extra={"correlation_id": correlation_id},
            )
            return None

    def _get_mock_secret(self, secret_name: str) -> Dict[str, Any]:
        """
        Generate mock secret data for development mode.

        Args:
            secret_name: Name of the secret

        Returns:
            Dictionary with development-friendly secret values
        """
        # Map common secret names to environment variable patterns
        if "app-credentials" in secret_name.lower():
            return {
                "database_url": settings.DATABASE_URL,
                "anthropic_api_key": settings.ANTHROPIC_API_KEY,
                "pinecone_api_key": settings.PINECONE_API_KEY,
                "clerk_secret_key": settings.CLERK_SECRET_KEY,
                "redis_url": settings.REDIS_URL,
            }
        elif "jwt" in secret_name.lower():
            return {"password": settings.SECRET_KEY}
        else:
            # Generic fallback
            return {"value": f"dev-mock-{secret_name}", "environment": "development"}

    async def health_check(self, correlation_id: str = "") -> Dict[str, Any]:
        """
        Check AWS Secrets Manager connectivity.

        Args:
            correlation_id: Request correlation ID for tracking

        Returns:
            Health status information
        """
        if self._mock_mode:
            return {"status": "healthy", "mode": "mock", "environment": "development"}

        try:
            if self._client is None:
                return {"status": "unhealthy", "error": "Client not initialized"}

            # Try to list secrets as a connectivity test
            response = self._client.list_secrets(MaxResults=1)

            return {
                "status": "healthy",
                "service": "AWS Secrets Manager",
                "region": getattr(settings, "AWS_REGION", "us-east-1"),
                "available_secrets": len(response.get("SecretList", [])),
            }

        except Exception as e:
            logger.error(
                f"AWS Secrets Manager health check failed: {str(e)}",
                extra={"correlation_id": correlation_id},
            )

            return {
                "status": "unhealthy",
                "error": str(e),
                "service": "AWS Secrets Manager",
            }

    def clear_cache(self) -> None:
        """Clear the secret cache."""
        self._cache.clear()
        logger.info("AWS Secrets Manager cache cleared")


# Global Secrets Manager client instance
secrets_client: Optional[SecretsManagerClient] = None


def get_secrets_client() -> SecretsManagerClient:
    """
    Get global Secrets Manager client instance.

    Returns:
        SecretsManager client instance
    """
    global secrets_client

    if secrets_client is None:
        secrets_client = SecretsManagerClient()

    return secrets_client
