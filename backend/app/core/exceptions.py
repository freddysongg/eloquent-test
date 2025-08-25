"""
Custom exception handlers and error response models.

Provides consistent error handling across the application with proper
logging, correlation IDs, and user-friendly error messages.
"""

import logging
import traceback
from typing import Any, Dict, Optional, Union

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.security import generate_correlation_id

logger = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error: Dict[str, Any] = Field(
        ..., description="Error details with message and metadata"
    )
    data: Optional[Any] = Field(
        default=None, description="Always null for error responses"
    )
    correlation_id: str = Field(
        ..., description="Unique identifier for request tracing"
    )
    timestamp: str = Field(..., description="ISO timestamp of error occurrence")


class AppException(Exception):
    """Base application exception with error context."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        """
        Initialize application exception.

        Args:
            message: Human-readable error message
            status_code: HTTP status code
            details: Additional error context
            correlation_id: Request correlation identifier
        """
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.correlation_id = correlation_id or generate_correlation_id()
        super().__init__(self.message)


class ValidationException(AppException):
    """Input validation error exception."""

    def __init__(
        self,
        message: str,
        field_errors: Optional[Dict[str, str]] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        """
        Initialize validation exception.

        Args:
            message: Validation error message
            field_errors: Field-specific error details
            correlation_id: Request correlation identifier
        """
        details = {"field_errors": field_errors or {}}
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
            correlation_id=correlation_id,
        )


class AuthenticationException(AppException):
    """Authentication error exception."""

    def __init__(
        self,
        message: str = "Authentication failed",
        correlation_id: Optional[str] = None,
    ) -> None:
        """
        Initialize authentication exception.

        Args:
            message: Authentication error message
            correlation_id: Request correlation identifier
        """
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            correlation_id=correlation_id,
        )


class AuthorizationException(AppException):
    """Authorization error exception."""

    def __init__(
        self, message: str = "Access denied", correlation_id: Optional[str] = None
    ) -> None:
        """
        Initialize authorization exception.

        Args:
            message: Authorization error message
            correlation_id: Request correlation identifier
        """
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            correlation_id=correlation_id,
        )


class ResourceNotFoundException(AppException):
    """Resource not found exception."""

    def __init__(
        self,
        resource_type: str,
        resource_id: Union[str, int],
        correlation_id: Optional[str] = None,
    ) -> None:
        """
        Initialize resource not found exception.

        Args:
            resource_type: Type of resource (e.g., 'chat', 'user')
            resource_id: Resource identifier
            correlation_id: Request correlation identifier
        """
        message = f"{resource_type.capitalize()} with ID {resource_id} not found"
        details = {"resource_type": resource_type, "resource_id": str(resource_id)}
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
            correlation_id=correlation_id,
        )


class RateLimitException(AppException):
    """Rate limit exceeded exception."""

    def __init__(
        self, limit_type: str, retry_after: int, correlation_id: Optional[str] = None
    ) -> None:
        """
        Initialize rate limit exception.

        Args:
            limit_type: Type of rate limit (e.g., 'global', 'user')
            retry_after: Seconds to wait before retrying
            correlation_id: Request correlation identifier
        """
        message = (
            f"Rate limit exceeded for {limit_type}. Try again in {retry_after} seconds."
        )
        details = {"limit_type": limit_type, "retry_after": retry_after}
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details,
            correlation_id=correlation_id,
        )


class ExternalServiceException(AppException):
    """External service integration error exception."""

    def __init__(
        self,
        service_name: str,
        error_message: str,
        correlation_id: Optional[str] = None,
    ) -> None:
        """
        Initialize external service exception.

        Args:
            service_name: Name of external service
            error_message: Service-specific error message
            correlation_id: Request correlation identifier
        """
        message = f"{service_name} service error: {error_message}"
        details = {"service_name": service_name, "service_error": error_message}
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
            correlation_id=correlation_id,
        )


async def app_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle custom application exceptions.

    Args:
        request: FastAPI request object
        exc: Exception instance (should be AppException)

    Returns:
        Standardized JSON error response
    """
    # Ensure it's our custom exception type
    if not isinstance(exc, AppException):
        # Convert to internal server error if it's not our exception type
        exc = ExternalServiceException(
            service_name="application",
            error_message=f"Unexpected error: {str(exc)}",
            correlation_id=generate_correlation_id(),
        )

    # Now we know exc is AppException type
    app_exc = exc  # Type is narrowed by isinstance check
    # Log error with correlation ID
    logger.error(
        f"Application exception: {app_exc.message}",
        extra={
            "correlation_id": app_exc.correlation_id,
            "status_code": app_exc.status_code,
            "details": app_exc.details,
            "path": str(request.url),
            "method": request.method,
        },
    )

    error_response = ErrorResponse(
        error={
            "message": app_exc.message,
            "code": app_exc.status_code,
            "details": app_exc.details,
        },
        data=None,
        correlation_id=app_exc.correlation_id,
        timestamp=(
            str(request.state.timestamp) if hasattr(request.state, "timestamp") else ""
        ),
    )

    return JSONResponse(status_code=app_exc.status_code, content=error_response.dict())


async def http_exception_handler_custom(
    request: Request, exc: Exception
) -> JSONResponse:
    """
    Handle FastAPI HTTP exceptions with consistent format.

    Args:
        request: FastAPI request object
        exc: Exception instance (should be HTTPException)

    Returns:
        Standardized JSON error response
    """
    # Ensure it's an HTTP exception
    if not isinstance(exc, HTTPException):
        # Convert to 500 error if it's not an HTTP exception
        exc = HTTPException(status_code=500, detail=str(exc))

    # Now we know exc is HTTPException type
    http_exc = exc  # Type is narrowed by isinstance check
    correlation_id = generate_correlation_id()

    # Log HTTP exception
    logger.warning(
        f"HTTP exception: {http_exc.detail}",
        extra={
            "correlation_id": correlation_id,
            "status_code": http_exc.status_code,
            "path": str(request.url),
            "method": request.method,
        },
    )

    error_response = ErrorResponse(
        error={"message": http_exc.detail, "code": http_exc.status_code, "details": {}},
        data=None,
        correlation_id=correlation_id,
        timestamp=(
            str(request.state.timestamp) if hasattr(request.state, "timestamp") else ""
        ),
    )

    return JSONResponse(status_code=http_exc.status_code, content=error_response.dict())


async def validation_exception_handler_custom(
    request: Request, exc: Exception
) -> JSONResponse:
    """
    Handle Pydantic validation errors with detailed field information.

    Args:
        request: FastAPI request object
        exc: Exception instance (should be RequestValidationError)

    Returns:
        Standardized JSON error response with validation details
    """
    # Ensure it's a validation error
    if not isinstance(exc, RequestValidationError):
        # Convert to generic validation error if it's not the expected type
        from fastapi.exceptions import RequestValidationError as RVE

        exc = RVE([{"loc": ["body"], "msg": str(exc), "type": "value_error"}])

    # Now we know exc is RequestValidationError type
    validation_exc = exc  # Type is narrowed by isinstance check
    correlation_id = generate_correlation_id()

    # Extract field-specific errors
    field_errors = {}
    for error in validation_exc.errors():
        field_path = ".".join(str(loc) for loc in error["loc"])
        field_errors[field_path] = error["msg"]

    logger.warning(
        f"Validation error: {len(field_errors)} field(s) invalid",
        extra={
            "correlation_id": correlation_id,
            "field_errors": field_errors,
            "path": str(request.url),
            "method": request.method,
        },
    )

    error_response = ErrorResponse(
        error={
            "message": "Request validation failed",
            "code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "details": {"field_errors": field_errors, "error_count": len(field_errors)},
        },
        data=None,
        correlation_id=correlation_id,
        timestamp=(
            str(request.state.timestamp) if hasattr(request.state, "timestamp") else ""
        ),
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=error_response.dict()
    )


async def internal_server_error_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """
    Handle unexpected internal server errors.

    Args:
        request: FastAPI request object
        exc: Unhandled exception instance

    Returns:
        Generic internal server error response
    """
    correlation_id = generate_correlation_id()

    # Log full stack trace for debugging
    logger.error(
        f"Internal server error: {str(exc)}",
        extra={
            "correlation_id": correlation_id,
            "path": str(request.url),
            "method": request.method,
            "traceback": traceback.format_exc(),
        },
    )

    # Don't expose internal error details to client
    error_response = ErrorResponse(
        error={
            "message": "Internal server error occurred",
            "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "details": {},
        },
        data=None,
        correlation_id=correlation_id,
        timestamp=(
            str(request.state.timestamp) if hasattr(request.state, "timestamp") else ""
        ),
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=error_response.dict()
    )
