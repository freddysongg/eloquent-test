"""
Rate limiting middleware for API protection and abuse prevention.

Implements multi-tier rate limiting with Redis backend:
- Global: 1000 req/min per IP
- Authenticated: 100 req/min per user  
- Anonymous: 20 req/min per session
- LLM calls: 10 req/min per user
"""

import logging
import time
from typing import Dict, Optional, Tuple

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.integrations.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class RateLimitConfig:
    """Rate limiting configuration and constants."""
    
    # Rate limits (requests per minute)
    GLOBAL_LIMIT = 1000
    AUTHENTICATED_LIMIT = 100
    ANONYMOUS_LIMIT = 20
    LLM_LIMIT = 10
    
    # Rate limit windows (seconds)
    GLOBAL_WINDOW = 60
    USER_WINDOW = 60
    LLM_WINDOW = 60
    
    # Redis key prefixes
    GLOBAL_PREFIX = "rate_limit:global"
    USER_PREFIX = "rate_limit:user"
    ANONYMOUS_PREFIX = "rate_limit:anonymous"
    LLM_PREFIX = "rate_limit:llm"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Multi-tier rate limiting middleware with Redis backend."""
    
    def __init__(self, app) -> None:
        """Initialize rate limiting middleware."""
        super().__init__(app)
        self.config = RateLimitConfig()
        logger.info("Rate limiting middleware initialized")
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request with rate limiting checks.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain
            
        Returns:
            HTTP response or rate limit error
        """
        correlation_id = getattr(request.state, 'correlation_id', '')
        
        try:
            # Skip rate limiting for health checks and static files
            if self._should_skip_rate_limiting(request):
                return await call_next(request)
            
            # Get client identifiers
            client_ip = self._get_client_ip(request)
            user_id = self._get_user_id(request)
            session_id = self._get_session_id(request)
            
            # Check rate limits in order of precedence
            rate_limit_result = await self._check_rate_limits(
                client_ip, user_id, session_id, request, correlation_id
            )
            
            if not rate_limit_result["allowed"]:
                return self._create_rate_limit_response(rate_limit_result, correlation_id)
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers to response
            self._add_rate_limit_headers(response, rate_limit_result)
            
            return response
            
        except Exception as e:
            logger.error(
                f"Rate limiting middleware error: {str(e)}",
                extra={"correlation_id": correlation_id}
            )
            # Fail open - allow request if rate limiting fails
            return await call_next(request)
    
    def _should_skip_rate_limiting(self, request: Request) -> bool:
        """
        Determine if rate limiting should be skipped for this request.
        
        Args:
            request: HTTP request
            
        Returns:
            True if rate limiting should be skipped
        """
        skip_paths = [
            "/health",
            "/metrics", 
            "/favicon.ico",
            "/static/",
            "/_next/"
        ]
        
        return any(request.url.path.startswith(path) for path in skip_paths)
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address from request headers.
        
        Args:
            request: HTTP request
            
        Returns:
            Client IP address
        """
        # Check forwarded headers first (for proxy/load balancer setups)
        forwarded_ips = [
            request.headers.get("X-Forwarded-For"),
            request.headers.get("X-Real-IP"),
            request.headers.get("CF-Connecting-IP")  # Cloudflare
        ]
        
        for ip in forwarded_ips:
            if ip:
                # Take first IP in comma-separated list
                return ip.split(",")[0].strip()
        
        # Fallback to direct connection IP
        return request.client.host if request.client else "unknown"
    
    def _get_user_id(self, request: Request) -> Optional[str]:
        """
        Get authenticated user ID from request.
        
        Args:
            request: HTTP request
            
        Returns:
            User ID if authenticated, None otherwise
        """
        # Check if user is set in request state (by auth middleware)
        user = getattr(request.state, 'user', None)
        if user:
            return str(user.id)
        
        # Check Authorization header for user ID
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # This would be extracted by auth middleware normally
            # For now, return None to indicate unauthenticated
            pass
        
        return None
    
    def _get_session_id(self, request: Request) -> str:
        """
        Get session ID for anonymous users.
        
        Args:
            request: HTTP request
            
        Returns:
            Session ID (IP-based fallback if no session cookie)
        """
        # Check for session cookie
        session_id = request.cookies.get("session_id")
        if session_id:
            return session_id
        
        # Fallback to IP-based session for anonymous users
        return f"ip:{self._get_client_ip(request)}"
    
    async def _check_rate_limits(
        self,
        client_ip: str,
        user_id: Optional[str],
        session_id: str,
        request: Request,
        correlation_id: str = ""
    ) -> Dict[str, any]:
        """
        Check all applicable rate limits for the request.
        
        Args:
            client_ip: Client IP address
            user_id: Authenticated user ID (if any)
            session_id: Session identifier
            request: HTTP request
            correlation_id: Request correlation ID
            
        Returns:
            Rate limit check result
        """
        redis_client = await get_redis_client()
        
        # Check global rate limit (per IP)
        global_check = await redis_client.check_rate_limit(
            f"{self.config.GLOBAL_PREFIX}:{client_ip}",
            self.config.GLOBAL_LIMIT,
            self.config.GLOBAL_WINDOW,
            correlation_id
        )
        
        if not global_check["allowed"]:
            logger.warning(
                f"Global rate limit exceeded",
                extra={
                    "client_ip": client_ip,
                    "limit": self.config.GLOBAL_LIMIT,
                    "current_count": global_check["current_count"],
                    "correlation_id": correlation_id
                }
            )
            return {
                **global_check,
                "limit_type": "global",
                "identifier": client_ip
            }
        
        # Check user-specific rate limits
        if user_id:
            # Authenticated user limit
            user_check = await redis_client.check_rate_limit(
                f"{self.config.USER_PREFIX}:{user_id}",
                self.config.AUTHENTICATED_LIMIT,
                self.config.USER_WINDOW,
                correlation_id
            )
            
            if not user_check["allowed"]:
                logger.warning(
                    f"User rate limit exceeded",
                    extra={
                        "user_id": user_id,
                        "limit": self.config.AUTHENTICATED_LIMIT,
                        "current_count": user_check["current_count"],
                        "correlation_id": correlation_id
                    }
                )
                return {
                    **user_check,
                    "limit_type": "user",
                    "identifier": user_id
                }
            
            # Check LLM-specific limits for AI endpoints
            if self._is_llm_endpoint(request):
                llm_check = await redis_client.check_rate_limit(
                    f"{self.config.LLM_PREFIX}:{user_id}",
                    self.config.LLM_LIMIT,
                    self.config.LLM_WINDOW,
                    correlation_id
                )
                
                if not llm_check["allowed"]:
                    logger.warning(
                        f"LLM rate limit exceeded",
                        extra={
                            "user_id": user_id,
                            "limit": self.config.LLM_LIMIT,
                            "current_count": llm_check["current_count"],
                            "correlation_id": correlation_id
                        }
                    )
                    return {
                        **llm_check,
                        "limit_type": "llm",
                        "identifier": user_id
                    }
                
                # Return LLM check result for header information
                return {
                    **llm_check,
                    "limit_type": "llm",
                    "identifier": user_id
                }
            
            # Return user check result
            return {
                **user_check,
                "limit_type": "user", 
                "identifier": user_id
            }
        
        else:
            # Anonymous user limit (session-based)
            anonymous_check = await redis_client.check_rate_limit(
                f"{self.config.ANONYMOUS_PREFIX}:{session_id}",
                self.config.ANONYMOUS_LIMIT,
                self.config.USER_WINDOW,
                correlation_id
            )
            
            if not anonymous_check["allowed"]:
                logger.warning(
                    f"Anonymous rate limit exceeded",
                    extra={
                        "session_id": session_id,
                        "limit": self.config.ANONYMOUS_LIMIT,
                        "current_count": anonymous_check["current_count"],
                        "correlation_id": correlation_id
                    }
                )
                return {
                    **anonymous_check,
                    "limit_type": "anonymous",
                    "identifier": session_id
                }
            
            return {
                **anonymous_check,
                "limit_type": "anonymous",
                "identifier": session_id
            }
    
    def _is_llm_endpoint(self, request: Request) -> bool:
        """
        Check if request is to an LLM/AI endpoint.
        
        Args:
            request: HTTP request
            
        Returns:
            True if this is an LLM endpoint
        """
        llm_paths = [
            "/v1/chat",
            "/v1/stream", 
            "/api/chat",
            "/api/stream",
            "/websocket"  # WebSocket chat endpoints
        ]
        
        return any(request.url.path.startswith(path) for path in llm_paths)
    
    def _create_rate_limit_response(
        self, 
        rate_limit_result: Dict[str, any],
        correlation_id: str = ""
    ) -> JSONResponse:
        """
        Create rate limit exceeded response.
        
        Args:
            rate_limit_result: Rate limit check result
            correlation_id: Request correlation ID
            
        Returns:
            JSON response with rate limit error
        """
        limit_type = rate_limit_result.get("limit_type", "unknown")
        limit = rate_limit_result.get("limit", 0)
        reset_time = rate_limit_result.get("reset_time", 60)
        
        error_message = f"Rate limit exceeded for {limit_type}. Limit: {limit} requests per minute."
        
        headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(time.time()) + reset_time),
            "X-RateLimit-Type": limit_type,
            "Retry-After": str(reset_time)
        }
        
        logger.info(
            f"Rate limit response sent",
            extra={
                "limit_type": limit_type,
                "limit": limit,
                "reset_time": reset_time,
                "correlation_id": correlation_id
            }
        )
        
        return JSONResponse(
            status_code=429,
            content={
                "data": None,
                "error": {
                    "message": error_message,
                    "code": "RATE_LIMIT_EXCEEDED",
                    "details": {
                        "limit": limit,
                        "reset_time": reset_time,
                        "limit_type": limit_type
                    }
                }
            },
            headers=headers
        )
    
    def _add_rate_limit_headers(
        self, 
        response: Response, 
        rate_limit_result: Dict[str, any]
    ) -> None:
        """
        Add rate limit headers to successful response.
        
        Args:
            response: HTTP response
            rate_limit_result: Rate limit check result
        """
        limit = rate_limit_result.get("limit", 0)
        remaining = rate_limit_result.get("remaining", 0)
        reset_time = rate_limit_result.get("reset_time", 60)
        limit_type = rate_limit_result.get("limit_type", "unknown")
        
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + reset_time)
        response.headers["X-RateLimit-Type"] = limit_type


async def check_rate_limit_decorator(
    identifier: str,
    limit: int,
    window: int,
    correlation_id: str = ""
) -> None:
    """
    Decorator function for manual rate limit checks.
    
    Args:
        identifier: Unique identifier for rate limiting
        limit: Maximum requests allowed
        window: Time window in seconds
        correlation_id: Request correlation ID
        
    Raises:
        HTTPException: If rate limit exceeded
    """
    redis_client = await get_redis_client()
    
    result = await redis_client.check_rate_limit(
        identifier,
        limit,
        window,
        correlation_id
    )
    
    if not result["allowed"]:
        raise HTTPException(
            status_code=429,
            detail={
                "message": f"Rate limit exceeded. Limit: {limit} requests per {window} seconds.",
                "code": "RATE_LIMIT_EXCEEDED",
                "details": {
                    "limit": limit,
                    "remaining": 0,
                    "reset_time": result.get("reset_time", window)
                }
            },
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time()) + result.get("reset_time", window)),
                "Retry-After": str(result.get("reset_time", window))
            }
        )