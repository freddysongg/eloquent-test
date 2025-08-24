"""
Main API router for version 1 endpoints.

Aggregates all endpoint routers with proper tagging and documentation.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, chat, users, webhooks


# Create main API router
api_router = APIRouter()

# Include endpoint routers with tags
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

api_router.include_router(
    users.router,
    prefix="/users",
    tags=["Users"]
)

api_router.include_router(
    chat.router,
    prefix="/chats",
    tags=["Chat"]
)

api_router.include_router(
    webhooks.router,
    prefix="/webhooks",
    tags=["Webhooks"]
)