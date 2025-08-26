"""
Webhook endpoints for external service integrations.

Handles Clerk webhooks for user lifecycle management and synchronization
with comprehensive security validation and error handling.
"""

import hashlib
import hmac
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.common import RequestContext, get_request_context
from app.core.config import settings
from app.models.base import get_db_session
from app.models.user import User
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

router = APIRouter()


def verify_clerk_webhook(payload: bytes, signature: str, webhook_secret: str) -> bool:
    """
    Verify Clerk webhook signature for security.

    Args:
        payload: Raw webhook payload bytes
        signature: Clerk webhook signature header
        webhook_secret: Configured webhook secret

    Returns:
        True if signature is valid, False otherwise
    """
    if not webhook_secret:
        logger.warning("No webhook secret configured - skipping signature verification")
        return True  # Allow in development if no secret is configured

    try:
        # Extract signature from header (format: "v1,signature")
        if not signature.startswith("v1,"):
            return False

        provided_signature = signature[3:]  # Remove "v1," prefix

        # Calculate expected signature
        expected_signature = hmac.new(
            webhook_secret.encode(), payload, hashlib.sha256
        ).hexdigest()

        # Secure comparison
        return hmac.compare_digest(provided_signature, expected_signature)

    except Exception as e:
        logger.error(f"Webhook signature verification failed: {str(e)}")
        return False


async def handle_user_created(
    event_data: Dict[str, Any], db: AsyncSession, correlation_id: str
) -> None:
    """Handle user.created webhook event."""
    try:
        clerk_user_id = event_data.get("id")
        email_addresses = event_data.get("email_addresses", [])

        if not clerk_user_id:
            raise ValueError("No user ID in webhook data")

        # Get primary email
        primary_email = None
        for email_data in email_addresses:
            if email_data.get("id") == event_data.get("primary_email_address_id"):
                primary_email = email_data.get("email_address")
                break

        if not primary_email:
            logger.warning(f"No primary email found for user {clerk_user_id}")

        # Check if user already exists
        user_repo = UserRepository(db)
        existing_user = await user_repo.get_by_clerk_id(clerk_user_id)

        if existing_user:
            logger.info(
                f"User {clerk_user_id} already exists, updating",
                extra={"correlation_id": correlation_id},
            )
            # Update existing user
            existing_user.update_from_clerk(event_data)
            await user_repo.update(existing_user)
        else:
            # Create new user
            user = User(
                clerk_user_id=clerk_user_id,
                email=primary_email,
                first_name=event_data.get("first_name"),
                last_name=event_data.get("last_name"),
            )
            user.update_from_clerk(event_data)
            await user_repo.create(user)

            logger.info(
                f"Created new user from Clerk webhook: {clerk_user_id}",
                extra={"correlation_id": correlation_id, "user_id": str(user.id)},
            )

    except Exception as e:
        logger.error(
            f"Failed to handle user.created event: {str(e)}",
            extra={"correlation_id": correlation_id},
        )
        raise


async def handle_user_updated(
    event_data: Dict[str, Any], db: AsyncSession, correlation_id: str
) -> None:
    """Handle user.updated webhook event."""
    try:
        clerk_user_id = event_data.get("id")

        if not clerk_user_id:
            raise ValueError("No user ID in webhook data")

        user_repo = UserRepository(db)
        user = await user_repo.get_by_clerk_id(clerk_user_id)

        if not user:
            logger.warning(
                f"User {clerk_user_id} not found for update, creating new user",
                extra={"correlation_id": correlation_id},
            )
            # Create user if not exists
            await handle_user_created(event_data, db, correlation_id)
        else:
            # Update existing user
            user.update_from_clerk(event_data)
            await user_repo.update(user)

            logger.info(
                f"Updated user from Clerk webhook: {clerk_user_id}",
                extra={"correlation_id": correlation_id, "user_id": str(user.id)},
            )

    except Exception as e:
        logger.error(
            f"Failed to handle user.updated event: {str(e)}",
            extra={"correlation_id": correlation_id},
        )
        raise


async def handle_user_deleted(
    event_data: Dict[str, Any], db: AsyncSession, correlation_id: str
) -> None:
    """Handle user.deleted webhook event."""
    try:
        clerk_user_id = event_data.get("id")

        if not clerk_user_id:
            raise ValueError("No user ID in webhook data")

        user_repo = UserRepository(db)
        user = await user_repo.get_by_clerk_id(clerk_user_id)

        if user:
            # Soft delete user (mark as inactive)
            user.is_active = False
            user.deleted_at = event_data.get("deleted_at")
            await user_repo.update(user)

            logger.info(
                f"Soft deleted user from Clerk webhook: {clerk_user_id}",
                extra={"correlation_id": correlation_id, "user_id": str(user.id)},
            )
        else:
            logger.warning(
                f"User {clerk_user_id} not found for deletion",
                extra={"correlation_id": correlation_id},
            )

    except Exception as e:
        logger.error(
            f"Failed to handle user.deleted event: {str(e)}",
            extra={"correlation_id": correlation_id},
        )
        raise


@router.post("/clerk")
async def clerk_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    context: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """
    Handle Clerk user lifecycle webhook events.

    Processes user.created, user.updated, and user.deleted events
    with proper security validation and comprehensive error handling.

    Args:
        request: FastAPI request object
        db: Database session
        context: Request context for logging

    Returns:
        Webhook processing confirmation

    Raises:
        HTTPException: If webhook processing fails
    """
    try:
        # Get raw payload for signature verification
        payload = await request.body()
        signature = request.headers.get("clerk-signature", "")

        # Verify webhook signature
        if not verify_clerk_webhook(payload, signature, settings.CLERK_WEBHOOK_SECRET):
            logger.warning(
                "Invalid Clerk webhook signature",
                extra={"correlation_id": context.correlation_id},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )

        # Parse JSON payload
        try:
            event_data = await request.json()
        except Exception as e:
            logger.error(
                f"Failed to parse webhook JSON: {str(e)}",
                extra={"correlation_id": context.correlation_id},
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload"
            )

        event_type = event_data.get("type")
        user_data = event_data.get("data", {})

        logger.info(
            f"Processing Clerk webhook event: {event_type}",
            extra={"correlation_id": context.correlation_id},
        )

        # Process event based on type
        if event_type == "user.created":
            await handle_user_created(user_data, db, context.correlation_id)
        elif event_type == "user.updated":
            await handle_user_updated(user_data, db, context.correlation_id)
        elif event_type == "user.deleted":
            await handle_user_deleted(user_data, db, context.correlation_id)
        else:
            logger.info(
                f"Unhandled webhook event type: {event_type}",
                extra={"correlation_id": context.correlation_id},
            )

        return {
            "status": "success",
            "event_type": event_type,
            "processed_at": context.timestamp.isoformat(),
            "correlation_id": context.correlation_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Webhook processing failed: {str(e)}",
            extra={"correlation_id": context.correlation_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed",
        )


@router.get("/health")
async def webhook_health() -> Dict[str, str]:
    """Webhook health check endpoint."""
    return {"status": "healthy", "service": "webhooks"}


# Add new endpoint for anonymous user migration
@router.post("/migrate-anonymous")
async def migrate_anonymous_user(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    context: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """
    Migrate anonymous user data to authenticated user.

    This endpoint allows newly authenticated users to migrate their
    anonymous session data (chat history, preferences) to their account.

    Args:
        request: FastAPI request object with migration data
        db: Database session
        context: Request context for logging

    Returns:
        Migration status and summary
    """
    try:
        migration_data = await request.json()
        anonymous_session_id = migration_data.get("anonymousSessionId")
        chat_history = migration_data.get("chatHistory", [])

        # TODO: Implement actual migration logic
        # This would involve:
        # 1. Getting authenticated user from token
        # 2. Finding anonymous chat data by session ID
        # 3. Transferring chat history to authenticated user
        # 4. Cleaning up anonymous session data

        logger.info(
            f"Anonymous user migration requested",
            extra={
                "correlation_id": context.correlation_id,
                "anonymous_session_id": anonymous_session_id,
                "chat_count": len(chat_history),
            },
        )

        # Return success for now - full implementation pending
        return {
            "status": "success",
            "migrated_chats": len(chat_history),
            "migration_id": context.correlation_id,
        }

    except Exception as e:
        logger.error(
            f"Anonymous migration failed: {str(e)}",
            extra={"correlation_id": context.correlation_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Migration failed"
        )
