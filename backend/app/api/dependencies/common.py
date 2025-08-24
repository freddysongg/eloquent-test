"""
Common dependencies for API endpoints.

Provides shared dependencies for pagination, rate limiting,
request validation, and correlation tracking.
"""

import time
from typing import Optional, Tuple
from uuid import uuid4

from fastapi import Depends, Header, Query, Request
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.security import generate_correlation_id


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""
    
    page: int = Field(
        default=1,
        ge=1,
        le=1000,
        description="Page number (1-indexed)"
    )
    
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Items per page (1-100)"
    )
    
    @property
    def offset(self) -> int:
        """Calculate database offset from page and limit."""
        return (self.page - 1) * self.limit


class SortParams(BaseModel):
    """Sorting parameters for list endpoints."""
    
    sort_by: str = Field(
        default="created_at",
        description="Field to sort by"
    )
    
    sort_order: str = Field(
        default="desc",
        regex="^(asc|desc)$",
        description="Sort order: asc or desc"
    )


async def get_pagination_params(
    page: int = Query(
        default=1,
        ge=1,
        le=1000,
        description="Page number (1-indexed)"
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Items per page (1-100)"
    )
) -> PaginationParams:
    """
    Get pagination parameters from query string.
    
    Args:
        page: Page number (1-indexed)
        limit: Items per page
    
    Returns:
        Pagination parameters object
    """
    return PaginationParams(page=page, limit=limit)


async def get_sort_params(
    sort_by: str = Query(
        default="created_at",
        description="Field to sort by"
    ),
    sort_order: str = Query(
        default="desc",
        regex="^(asc|desc)$",
        description="Sort order: asc or desc"
    )
) -> SortParams:
    """
    Get sort parameters from query string.
    
    Args:
        sort_by: Field name to sort by
        sort_order: Sort direction (asc or desc)
    
    Returns:
        Sort parameters object
    """
    return SortParams(sort_by=sort_by, sort_order=sort_order)


async def get_correlation_id(
    request: Request,
    x_correlation_id: Optional[str] = Header(None)
) -> str:
    """
    Get or generate correlation ID for request tracking.
    
    Args:
        request: FastAPI request object
        x_correlation_id: Optional correlation ID from header
    
    Returns:
        Correlation ID for request tracing
    """
    # Use provided correlation ID or generate new one
    correlation_id = x_correlation_id or generate_correlation_id()
    
    # Store in request state for use in other dependencies
    request.state.correlation_id = correlation_id
    
    return correlation_id


async def get_request_timestamp(request: Request) -> float:
    """
    Get request timestamp for performance tracking.
    
    Args:
        request: FastAPI request object
    
    Returns:
        Request timestamp as Unix timestamp
    """
    timestamp = time.time()
    request.state.timestamp = timestamp
    return timestamp


class RequestContext(BaseModel):
    """Request context information for endpoints."""
    
    correlation_id: str
    timestamp: float
    user_agent: Optional[str] = None
    client_ip: Optional[str] = None


async def get_request_context(
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    timestamp: float = Depends(get_request_timestamp),
    user_agent: Optional[str] = Header(None)
) -> RequestContext:
    """
    Get comprehensive request context information.
    
    Args:
        request: FastAPI request object
        correlation_id: Request correlation ID
        timestamp: Request timestamp
        user_agent: Client user agent string
    
    Returns:
        Request context object with tracking information
    """
    # Get client IP from headers or connection
    client_ip = (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or request.headers.get("x-real-ip")
        or str(request.client.host) if request.client else None
    )
    
    return RequestContext(
        correlation_id=correlation_id,
        timestamp=timestamp,
        user_agent=user_agent,
        client_ip=client_ip
    )


def get_cache_key(*args: str) -> str:
    """
    Generate cache key from arguments.
    
    Args:
        *args: Cache key components
    
    Returns:
        Formatted cache key string
    """
    return ":".join(str(arg) for arg in args)


async def get_list_params(
    pagination: PaginationParams = Depends(get_pagination_params),
    sort: SortParams = Depends(get_sort_params)
) -> Tuple[PaginationParams, SortParams]:
    """
    Get combined pagination and sort parameters.
    
    Args:
        pagination: Pagination parameters
        sort: Sort parameters
    
    Returns:
        Tuple of (pagination, sort) parameters
    """
    return pagination, sort