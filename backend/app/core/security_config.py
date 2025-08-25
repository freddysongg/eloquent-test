"""
Production Security Configuration for EloquentAI Backend
Enhanced security settings for production deployment.
"""

import os
import secrets
from typing import Dict, List, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware


class ProductionSecurityConfig:
    """Production security configuration and middleware setup."""

    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.is_production = self.environment == "production"

    @property
    def cors_config(self) -> Dict:
        """CORS configuration based on environment."""
        if self.is_production:
            # Strict CORS for production
            return {
                "allow_origins": [
                    "https://eloquentai.com",
                    "https://www.eloquentai.com",
                    "https://app.eloquentai.com",
                ],
                "allow_credentials": True,
                "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": [
                    "Authorization",
                    "Content-Type",
                    "X-Requested-With",
                    "X-CSRF-Token",
                    "X-Request-ID",
                ],
                "expose_headers": [
                    "X-RateLimit-Limit",
                    "X-RateLimit-Remaining",
                    "X-RateLimit-Reset",
                    "X-Request-ID",
                ],
                "max_age": 86400,  # 24 hours
            }
        else:
            # Development CORS
            return {
                "allow_origins": ["*"],
                "allow_credentials": True,
                "allow_methods": ["*"],
                "allow_headers": ["*"],
            }

    @property
    def trusted_hosts(self) -> List[str]:
        """Trusted hosts configuration."""
        if self.is_production:
            return [
                "eloquentai.com",
                "*.eloquentai.com",
                "api.eloquentai.com",
                "*.execute-api.us-east-1.amazonaws.com",  # API Gateway
                "*.apprunner.amazonaws.com",  # App Runner domains
            ]
        else:
            return ["*"]

    @property
    def security_headers(self) -> Dict[str, str]:
        """Security headers for responses."""
        headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }

        if self.is_production:
            headers.update(
                {
                    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
                    "Content-Security-Policy": (
                        "default-src 'self'; "
                        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                        "style-src 'self' 'unsafe-inline'; "
                        "img-src 'self' data: https:; "
                        "font-src 'self'; "
                        "connect-src 'self' https://api.anthropic.com https://*.pinecone.io; "
                        "frame-ancestors 'none'; "
                        "base-uri 'self'; "
                        "form-action 'self'"
                    ),
                }
            )

        return headers

    @property
    def session_config(self) -> Dict:
        """Session middleware configuration."""
        return {
            "secret_key": os.getenv("SESSION_SECRET_KEY", secrets.token_urlsafe(32)),
            "max_age": 86400,  # 24 hours
            "same_site": "strict" if self.is_production else "lax",
            "https_only": self.is_production,
        }

    def get_rate_limit_config(self) -> Dict:
        """Rate limiting configuration by user type."""
        return {
            "global": {
                "requests": 1000,
                "window": 60,  # per minute
                "message": "Global rate limit exceeded",
            },
            "authenticated": {
                "requests": 100,
                "window": 60,  # per minute
                "message": "User rate limit exceeded",
            },
            "anonymous": {
                "requests": 20,
                "window": 60,  # per minute
                "message": "Anonymous rate limit exceeded",
            },
            "llm_calls": {
                "requests": 10,
                "window": 60,  # per minute
                "message": "LLM API rate limit exceeded",
            },
        }

    def validate_jwt_token(self, token: str) -> Dict:
        """Validate JWT token (placeholder - integrate with Clerk)."""
        # TODO: Implement actual JWT validation with Clerk
        if not token or token == "invalid.jwt.token":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
        return {"user_id": "validated_user"}

    def add_security_middleware(self, app):
        """Add all security middleware to FastAPI app."""

        # HTTPS redirect for production
        if self.is_production:
            app.add_middleware(HTTPSRedirectMiddleware)

        # Trusted hosts middleware
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=self.trusted_hosts)

        # Session middleware
        session_config = self.session_config
        app.add_middleware(
            SessionMiddleware,
            secret_key=session_config["secret_key"],
            max_age=session_config["max_age"],
            same_site=session_config["same_site"],
            https_only=session_config["https_only"],
        )

        # CORS middleware
        cors_config = self.cors_config
        app.add_middleware(CORSMiddleware, **cors_config)

        # Custom security headers middleware
        @app.middleware("http")
        async def add_security_headers(request: Request, call_next):
            response = await call_next(request)

            # Add security headers
            for header, value in self.security_headers.items():
                response.headers[header] = value

            # Add request ID for tracing
            request_id = getattr(request.state, "request_id", None)
            if request_id:
                response.headers["X-Request-ID"] = request_id

            return response

        return app


class SecurityHeaders:
    """Security headers utility class."""

    @staticmethod
    def get_cors_headers(origin: Optional[str] = None) -> Dict[str, str]:
        """Get CORS headers for manual responses."""
        config = ProductionSecurityConfig()
        cors_config = config.cors_config

        headers = {
            "Access-Control-Allow-Methods": ", ".join(
                cors_config.get("allow_methods", [])
            ),
            "Access-Control-Allow-Headers": ", ".join(
                cors_config.get("allow_headers", [])
            ),
            "Access-Control-Max-Age": str(cors_config.get("max_age", 86400)),
        }

        # Handle origin validation
        allowed_origins = cors_config.get("allow_origins", [])
        if origin and (origin in allowed_origins or "*" in allowed_origins):
            headers["Access-Control-Allow-Origin"] = origin
            if cors_config.get("allow_credentials"):
                headers["Access-Control-Allow-Credentials"] = "true"

        return headers

    @staticmethod
    def validate_content_type(request: Request, allowed_types: List[str]) -> bool:
        """Validate request content type."""
        content_type = request.headers.get("content-type", "").lower()
        return any(allowed_type in content_type for allowed_type in allowed_types)

    @staticmethod
    def sanitize_user_input(input_string: str, max_length: int = 1000) -> str:
        """Basic input sanitization."""
        if not input_string:
            return ""

        # Truncate if too long
        sanitized = input_string[:max_length]

        # Remove potential XSS patterns
        dangerous_patterns = ["<script", "javascript:", "data:", "vbscript:", "onload="]
        for pattern in dangerous_patterns:
            sanitized = sanitized.replace(pattern.lower(), "")
            sanitized = sanitized.replace(pattern.upper(), "")

        return sanitized.strip()


# Global security configuration instance
security_config = ProductionSecurityConfig()

# Security dependency for protected routes
security = HTTPBearer()


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency for verifying JWT tokens."""
    try:
        token = credentials.credentials
        user_data = security_config.validate_jwt_token(token)
        return user_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Export common security utilities
__all__ = [
    "ProductionSecurityConfig",
    "SecurityHeaders",
    "security_config",
    "verify_token",
    "security",
]
