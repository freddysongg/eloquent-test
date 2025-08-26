"""
Main FastAPI application for Eloquent AI backend.

Production-ready FastAPI app with middleware, exception handling,
CORS configuration, and API routing with WebSocket support.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Awaitable, Callable

from fastapi import FastAPI, Request, Response, WebSocket
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    http_exception_handler_custom,
    internal_server_error_handler,
    validation_exception_handler_custom,
)
from app.core.security import SecurityHeaders
from app.core.websocket import websocket_handler
from app.integrations.redis_client import close_redis, get_redis_client
from app.middleware.rate_limiting import RateLimitMiddleware
from app.models.base import close_db, init_db

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager for startup and shutdown events.

    Args:
        app: FastAPI application instance

    Yields:
        None during application lifetime
    """
    # Startup
    logger.info("Starting Eloquent AI Backend...")

    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized successfully")

        # Initialize Redis connection
        redis_client = await get_redis_client()
        redis_health = await redis_client.health_check()
        if redis_health:
            logger.info("Redis connection established")
        else:
            logger.warning("Redis connection failed - some features may be limited")

        # Additional startup tasks can be added here
        # - External service health checks
        # - Cache warming

        logger.info("Application startup complete")

    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Eloquent AI Backend...")

    try:
        # Close database connections
        await close_db()
        logger.info("Database connections closed")

        # Close Redis connections
        await close_redis()
        logger.info("Redis connections closed")

        # Additional cleanup tasks
        # - Cleanup background tasks
        # - Flush metrics

        logger.info("Application shutdown complete")

    except Exception as e:
        logger.error(f"Shutdown error: {str(e)}")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered chatbot with RAG for fintech FAQ support",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)


# Security middleware - add trusted host middleware
if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*.eloquentai.com"],
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def security_headers_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """
    Add security headers to all responses.

    Args:
        request: FastAPI request object
        call_next: Next middleware in chain

    Returns:
        Response with security headers added
    """
    response = await call_next(request)

    # Add security headers
    security_headers = SecurityHeaders.get_security_headers()
    for header_name, header_value in security_headers.items():
        response.headers[header_name] = header_value

    return response


@app.middleware("http")
async def logging_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """
    Log all requests with performance metrics.

    Args:
        request: FastAPI request object
        call_next: Next middleware in chain

    Returns:
        Response with logging and metrics recorded
    """
    start_time = time.time()

    # Get correlation ID from request state (set by dependency)
    correlation_id = getattr(request.state, "correlation_id", "unknown")

    # Log request start
    logger.info(
        f"Request started: {request.method} {request.url.path}",
        extra={
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "client_ip": request.client.host if request.client else None,
        },
    )

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = time.time() - start_time

    # Record metrics
    if settings.PROMETHEUS_METRICS_ENABLED:
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
        ).inc()

        REQUEST_DURATION.labels(
            method=request.method, endpoint=request.url.path
        ).observe(duration)

    # Log request completion
    logger.info(
        f"Request completed: {request.method} {request.url.path} - {response.status_code}",
        extra={
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
        },
    )

    return response


# WebSocket endpoint for real-time chat
@app.websocket("/ws/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: str) -> None:
    """
    WebSocket endpoint for real-time chat functionality with JWT authentication.

    Supports both authenticated and anonymous users:
    - Authenticated: Pass JWT token via Authorization header or query param
    - Anonymous: Connect without token, use session_id for identification

    Args:
        websocket: WebSocket connection
        chat_id: Chat room identifier
    """
    from app.api.dependencies.auth import get_websocket_user
    from app.api.dependencies.common import get_websocket_correlation_id

    # Get correlation ID for tracking
    correlation_id = get_websocket_correlation_id(websocket)

    # Authenticate user from JWT token or allow anonymous access
    user, session_id = await get_websocket_user(websocket, correlation_id)

    # Extract user_id for connection tracking
    user_id = str(user.id) if user else None

    logger.info(
        f"WebSocket connection request",
        extra={
            "chat_id": chat_id,
            "user_id": user_id,
            "session_id": session_id,
            "correlation_id": correlation_id,
            "authenticated": user is not None,
        },
    )

    await websocket_handler(websocket, user_id, chat_id, correlation_id)


# Exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler_custom)
app.add_exception_handler(RequestValidationError, validation_exception_handler_custom)
app.add_exception_handler(Exception, internal_server_error_handler)


# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check() -> dict:
    """
    Health check endpoint for load balancers and monitoring.

    Returns:
        Health status information
    """
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": time.time(),
    }


# Metrics endpoint for Prometheus
@app.get("/metrics", tags=["System"])
async def metrics() -> Response:
    """
    Prometheus metrics endpoint.

    Returns:
        Prometheus metrics in text format
    """
    if not settings.PROMETHEUS_METRICS_ENABLED:
        return JSONResponse(status_code=404, content={"error": "Metrics disabled"})

    return Response(content=generate_latest(), media_type="text/plain")


# API router
app.include_router(api_router, prefix="/v1")


# Root endpoint
@app.get("/", tags=["Root"])
async def root() -> dict:
    """
    Root endpoint with API information.

    Returns:
        API metadata and status
    """
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "docs_url": "/docs" if settings.DEBUG else None,
        "health_check": "/health",
        "api_prefix": "/v1",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL.lower(),
    )
