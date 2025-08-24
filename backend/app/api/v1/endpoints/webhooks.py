"""
Webhook endpoints for external service integrations (stub implementation).

TODO: Complete implementation with Integration Agent.
Handles Clerk webhooks for user synchronization.
"""

from fastapi import APIRouter, Depends
from app.api.dependencies.common import RequestContext, get_request_context

router = APIRouter()

@router.post("/clerk")
async def clerk_webhook(
    context: RequestContext = Depends(get_request_context)
) -> dict:
    """Handle Clerk user events webhook."""
    return {"message": "Clerk webhook endpoint - TODO: Implement"}

@router.get("/health")
async def webhook_health() -> dict:
    """Webhook health check endpoint."""
    return {"status": "healthy", "service": "webhooks"}