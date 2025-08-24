"""
Redis client for caching, rate limiting, and session management.

Implements async Redis client with connection pooling, pub/sub support,
and specialized methods for chat application features.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union

import redis.asyncio as redis
from redis.exceptions import ConnectionError, RedisError

from app.core.config import settings
from app.core.exceptions import ExternalServiceException

logger = logging.getLogger(__name__)


class RedisClient:
    """Async Redis client for caching and session management."""
    
    def __init__(self) -> None:
        """Initialize Redis connection pool."""
        try:
            self.pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                max_connections=20,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
            
            self.redis = redis.Redis(connection_pool=self.pool)
            
            logger.info("Redis client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {str(e)}")
            raise ExternalServiceException(
                "Redis",
                f"Client initialization failed: {str(e)}"
            )
    
    async def get(
        self,
        key: str,
        correlation_id: str = ""
    ) -> Optional[str]:
        """
        Get value by key from Redis.
        
        Args:
            key: Redis key
            correlation_id: Request correlation ID for tracking
        
        Returns:
            Value as string or None if not found
        
        Raises:
            ExternalServiceException: If Redis operation fails
        """
        try:
            value = await self.redis.get(key)
            
            logger.debug(
                f"Redis GET: {key} -> {'found' if value else 'not found'}",
                extra={"correlation_id": correlation_id}
            )
            
            return value
            
        except RedisError as e:
            logger.error(
                f"Redis GET failed for key '{key}': {str(e)}",
                extra={"correlation_id": correlation_id}
            )
            raise ExternalServiceException(
                "Redis",
                f"GET operation failed: {str(e)}",
                correlation_id=correlation_id
            )
    
    async def set(
        self,
        key: str,
        value: str,
        expiration: Optional[int] = None,
        correlation_id: str = ""
    ) -> bool:
        """
        Set key-value pair in Redis with optional expiration.
        
        Args:
            key: Redis key
            value: Value to store
            expiration: TTL in seconds
            correlation_id: Request correlation ID for tracking
        
        Returns:
            True if successful, False otherwise
        
        Raises:
            ExternalServiceException: If Redis operation fails
        """
        try:
            result = await self.redis.set(key, value, ex=expiration)
            
            logger.debug(
                f"Redis SET: {key} (TTL: {expiration}s) -> {'success' if result else 'failed'}",
                extra={"correlation_id": correlation_id}
            )
            
            return bool(result)
            
        except RedisError as e:
            logger.error(
                f"Redis SET failed for key '{key}': {str(e)}",
                extra={"correlation_id": correlation_id}
            )
            raise ExternalServiceException(
                "Redis",
                f"SET operation failed: {str(e)}",
                correlation_id=correlation_id
            )
    
    async def get_json(
        self,
        key: str,
        correlation_id: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Get JSON value from Redis.
        
        Args:
            key: Redis key
            correlation_id: Request correlation ID for tracking
        
        Returns:
            Parsed JSON data or None if not found
        """
        try:
            value = await self.get(key, correlation_id)
            
            if value is None:
                return None
            
            return json.loads(value)
            
        except json.JSONDecodeError as e:
            logger.error(
                f"JSON decode failed for key '{key}': {str(e)}",
                extra={"correlation_id": correlation_id}
            )
            return None
        except Exception as e:
            logger.error(
                f"Redis JSON GET failed for key '{key}': {str(e)}",
                extra={"correlation_id": correlation_id}
            )
            return None
    
    async def set_json(
        self,
        key: str,
        value: Dict[str, Any],
        expiration: Optional[int] = None,
        correlation_id: str = ""
    ) -> bool:
        """
        Set JSON value in Redis.
        
        Args:
            key: Redis key
            value: JSON-serializable data
            expiration: TTL in seconds
            correlation_id: Request correlation ID for tracking
        
        Returns:
            True if successful, False otherwise
        """
        try:
            json_value = json.dumps(value, default=str)
            return await self.set(key, json_value, expiration, correlation_id)
            
        except (TypeError, ValueError) as e:
            logger.error(
                f"JSON encode failed for key '{key}': {str(e)}",
                extra={"correlation_id": correlation_id}
            )
            return False
    
    async def delete(
        self,
        key: str,
        correlation_id: str = ""
    ) -> bool:
        """
        Delete key from Redis.
        
        Args:
            key: Redis key to delete
            correlation_id: Request correlation ID for tracking
        
        Returns:
            True if key was deleted, False if key didn't exist
        """
        try:
            result = await self.redis.delete(key)
            
            logger.debug(
                f"Redis DELETE: {key} -> {'success' if result else 'key not found'}",
                extra={"correlation_id": correlation_id}
            )
            
            return bool(result)
            
        except RedisError as e:
            logger.error(
                f"Redis DELETE failed for key '{key}': {str(e)}",
                extra={"correlation_id": correlation_id}
            )
            raise ExternalServiceException(
                "Redis",
                f"DELETE operation failed: {str(e)}",
                correlation_id=correlation_id
            )
    
    async def increment_counter(
        self,
        key: str,
        increment: int = 1,
        expiration: Optional[int] = None,
        correlation_id: str = ""
    ) -> int:
        """
        Increment counter in Redis (atomic operation).
        
        Args:
            key: Redis key for counter
            increment: Amount to increment by
            expiration: TTL in seconds (set only if key is new)
            correlation_id: Request correlation ID for tracking
        
        Returns:
            New counter value
        
        Raises:
            ExternalServiceException: If Redis operation fails
        """
        try:
            # Use pipeline for atomic increment and expiration
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.incrby(key, increment)
                
                # Set expiration only if this is a new key
                if expiration:
                    pipe.expire(key, expiration, nx=True)
                
                results = await pipe.execute()
                
            new_value = results[0]
            
            logger.debug(
                f"Redis INCREMENT: {key} +{increment} -> {new_value}",
                extra={"correlation_id": correlation_id}
            )
            
            return new_value
            
        except RedisError as e:
            logger.error(
                f"Redis INCREMENT failed for key '{key}': {str(e)}",
                extra={"correlation_id": correlation_id}
            )
            raise ExternalServiceException(
                "Redis",
                f"INCREMENT operation failed: {str(e)}",
                correlation_id=correlation_id
            )
    
    async def check_rate_limit(
        self,
        identifier: str,
        limit: int,
        window_seconds: int,
        correlation_id: str = ""
    ) -> Dict[str, Any]:
        """
        Check and update rate limit for identifier.
        
        Args:
            identifier: Unique identifier (user ID, IP, etc.)
            limit: Maximum requests allowed
            window_seconds: Time window in seconds
            correlation_id: Request correlation ID for tracking
        
        Returns:
            Rate limit status with remaining count and reset time
        """
        try:
            key = f"rate_limit:{identifier}:{window_seconds}"
            
            # Increment counter and get current value
            current_count = await self.increment_counter(
                key,
                increment=1,
                expiration=window_seconds,
                correlation_id=correlation_id
            )
            
            # Get TTL for reset time calculation
            ttl = await self.redis.ttl(key)
            
            rate_limit_status = {
                "allowed": current_count <= limit,
                "limit": limit,
                "remaining": max(0, limit - current_count),
                "reset_time": ttl,
                "current_count": current_count
            }
            
            logger.debug(
                f"Rate limit check: {identifier} -> {current_count}/{limit}",
                extra={"correlation_id": correlation_id}
            )
            
            return rate_limit_status
            
        except Exception as e:
            logger.error(
                f"Rate limit check failed for '{identifier}': {str(e)}",
                extra={"correlation_id": correlation_id}
            )
            # Fail open - allow request if Redis is down
            return {
                "allowed": True,
                "limit": limit,
                "remaining": limit - 1,
                "reset_time": window_seconds,
                "current_count": 1
            }
    
    async def store_chat_message(
        self,
        chat_id: str,
        message: Dict[str, Any],
        correlation_id: str = ""
    ) -> bool:
        """
        Store chat message in Redis for caching.
        
        Args:
            chat_id: Chat conversation ID
            message: Message data to store
            correlation_id: Request correlation ID for tracking
        
        Returns:
            True if successful, False otherwise
        """
        try:
            key = f"chat_messages:{chat_id}"
            
            # Store as JSON with 1 hour TTL
            return await self.set_json(
                key,
                message,
                expiration=3600,
                correlation_id=correlation_id
            )
            
        except Exception as e:
            logger.error(
                f"Failed to store chat message: {str(e)}",
                extra={"correlation_id": correlation_id}
            )
            return False
    
    async def get_chat_messages(
        self,
        chat_id: str,
        correlation_id: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached chat messages from Redis.
        
        Args:
            chat_id: Chat conversation ID
            correlation_id: Request correlation ID for tracking
        
        Returns:
            Cached message data or None if not found
        """
        try:
            key = f"chat_messages:{chat_id}"
            return await self.get_json(key, correlation_id)
            
        except Exception as e:
            logger.error(
                f"Failed to get chat messages: {str(e)}",
                extra={"correlation_id": correlation_id}
            )
            return None
    
    async def health_check(self) -> bool:
        """
        Check Redis connection health.
        
        Returns:
            True if Redis is healthy, False otherwise
        """
        try:
            # Simple ping test
            result = await self.redis.ping()
            return result is True
            
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            return False
    
    async def close(self) -> None:
        """Close Redis connection pool."""
        try:
            await self.redis.close()
            logger.info("Redis connection pool closed")
            
        except Exception as e:
            logger.error(f"Error closing Redis connection: {str(e)}")


# Global Redis client instance
redis_client: Optional[RedisClient] = None


async def get_redis_client() -> RedisClient:
    """
    Get global Redis client instance.
    
    Returns:
        Redis client instance
    """
    global redis_client
    
    if redis_client is None:
        redis_client = RedisClient()
    
    return redis_client


async def close_redis() -> None:
    """Close global Redis client."""
    global redis_client
    
    if redis_client:
        await redis_client.close()
        redis_client = None