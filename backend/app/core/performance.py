"""
Production Performance Optimization for EloquentAI Backend
Caching strategies, connection pooling, and performance monitoring.
"""

import asyncio
import hashlib
import json
import logging
import pickle
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Union

import psutil
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import QueuePool

from app.core.config import settings

logger = logging.getLogger(__name__)


class PerformanceConfig:
    """Performance optimization configuration."""

    def __init__(self):
        self.environment = settings.ENVIRONMENT
        self.is_production = self.environment == "production"

    @property
    def database_pool_config(self) -> Dict:
        """Database connection pool configuration."""
        if self.is_production:
            return {
                "pool_size": 20,  # Base number of connections
                "max_overflow": 30,  # Additional connections under load
                "pool_timeout": 30,  # Seconds to wait for connection
                "pool_recycle": 3600,  # Recycle connections every hour
                "pool_pre_ping": True,  # Validate connections
                "poolclass": QueuePool,
            }
        else:
            return {
                "pool_size": 5,
                "max_overflow": 10,
                "pool_timeout": 10,
                "pool_recycle": 1800,
                "pool_pre_ping": True,
                "poolclass": QueuePool,
            }

    @property
    def redis_pool_config(self) -> Dict:
        """Redis connection pool configuration."""
        if self.is_production:
            return {
                "max_connections": 50,
                "retry_on_timeout": True,
                "socket_timeout": 5,
                "socket_connect_timeout": 5,
                "health_check_interval": 30,
            }
        else:
            return {
                "max_connections": 10,
                "retry_on_timeout": True,
                "socket_timeout": 3,
                "socket_connect_timeout": 3,
                "health_check_interval": 60,
            }

    @property
    def cache_ttl_config(self) -> Dict[str, int]:
        """Cache TTL configuration by data type."""
        return {
            "chat_history": 3600,  # 1 hour
            "user_session": 86400,  # 24 hours
            "rag_results": 900,  # 15 minutes
            "embeddings": 7200,  # 2 hours
            "rate_limit": 60,  # 1 minute
            "health_check": 30,  # 30 seconds
            "api_response": 300,  # 5 minutes
        }


class RedisCache:
    """Production-ready Redis cache implementation."""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.pool = None
        self.client = None
        self.config = PerformanceConfig()

    async def connect(self):
        """Initialize Redis connection pool."""
        try:
            pool_config = self.config.redis_pool_config
            self.pool = redis.ConnectionPool.from_url(
                self.redis_url,
                **pool_config,
                decode_responses=False,  # Handle binary data
            )
            self.client = redis.Redis(connection_pool=self.pool)

            # Test connection
            await self.client.ping()
            logger.info("✅ Redis cache connected successfully")

        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            raise

    async def disconnect(self):
        """Close Redis connections."""
        if self.client:
            await self.client.close()
        if self.pool:
            await self.pool.disconnect()

    def _generate_key(self, prefix: str, identifier: str, **kwargs) -> str:
        """Generate cache key with optional parameters."""
        key_parts = [prefix, identifier]

        # Add sorted kwargs for consistent key generation
        if kwargs:
            sorted_params = sorted(kwargs.items())
            param_hash = hashlib.md5(str(sorted_params).encode()).hexdigest()[:8]
            key_parts.append(param_hash)

        return ":".join(key_parts)

    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache with automatic deserialization."""
        try:
            if not self.client:
                return default

            cached_data = await self.client.get(key)
            if cached_data is None:
                return default

            # Try to deserialize
            try:
                return pickle.loads(cached_data)
            except (pickle.PickleError, TypeError):
                # Fallback for string data
                return cached_data.decode("utf-8")

        except Exception as e:
            logger.warning(f"Cache get failed for key {key}: {e}")
            return default

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        cache_type: str = "default",
    ):
        """Set value in cache with automatic serialization."""
        try:
            if not self.client:
                return

            # Get TTL from configuration
            if ttl is None:
                ttl_config = self.config.cache_ttl_config
                ttl = ttl_config.get(cache_type, 300)  # Default 5 minutes

            # Serialize value
            if isinstance(value, (str, int, float, bool)):
                cache_data = str(value).encode("utf-8")
            else:
                cache_data = pickle.dumps(value)

            await self.client.setex(key, ttl, cache_data)

        except Exception as e:
            logger.warning(f"Cache set failed for key {key}: {e}")

    async def delete(self, key: str):
        """Delete key from cache."""
        try:
            if self.client:
                await self.client.delete(key)
        except Exception as e:
            logger.warning(f"Cache delete failed for key {key}: {e}")

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            if not self.client:
                return False
            return bool(await self.client.exists(key))
        except Exception as e:
            logger.warning(f"Cache exists check failed for key {key}: {e}")
            return False

    async def increment(self, key: str, amount: int = 1, ttl: int = 60) -> int:
        """Increment counter with TTL."""
        try:
            if not self.client:
                return amount

            # Use pipeline for atomic operation
            async with self.client.pipeline() as pipe:
                await pipe.incr(key, amount)
                await pipe.expire(key, ttl)
                results = await pipe.execute()
                return results[0]

        except Exception as e:
            logger.warning(f"Cache increment failed for key {key}: {e}")
            return amount

    async def health_check(self) -> Dict[str, Any]:
        """Redis health check with metrics."""
        try:
            if not self.client:
                return {"status": "disconnected", "error": "No client"}

            start_time = time.time()
            info = await self.client.info()
            ping_time = (time.time() - start_time) * 1000  # ms

            return {
                "status": "healthy",
                "ping_time_ms": round(ping_time, 2),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "N/A"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(info),
            }

        except Exception as e:
            return {"status": "unhealthy", "error": str(e), "ping_time_ms": None}

    def _calculate_hit_rate(self, info: Dict) -> float:
        """Calculate cache hit rate percentage."""
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses

        if total == 0:
            return 0.0

        return round((hits / total) * 100, 2)


class DatabasePerformance:
    """Database performance optimization utilities."""

    def __init__(self):
        self.config = PerformanceConfig()

    def create_optimized_engine(self, database_url: str):
        """Create database engine with production optimizations."""
        pool_config = self.config.database_pool_config

        engine = create_async_engine(
            database_url,
            **pool_config,
            echo=False if self.config.is_production else True,
            future=True,
        )

        return engine

    async def health_check(self, engine) -> Dict[str, Any]:
        """Database health check with connection pool metrics."""
        try:
            start_time = time.time()

            # Test basic connectivity
            async with engine.begin() as conn:
                result = await conn.execute("SELECT 1")
                await result.fetchone()

            response_time = (time.time() - start_time) * 1000  # ms

            # Get pool statistics
            pool = engine.pool

            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "pool_size": pool.size(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "checked_in": pool.checkedin(),
            }

        except Exception as e:
            return {"status": "unhealthy", "error": str(e), "response_time_ms": None}


class CacheDecorator:
    """Decorator for automatic caching of function results."""

    def __init__(self, redis_cache: RedisCache):
        self.cache = redis_cache

    def cached(
        self,
        cache_type: str = "default",
        ttl: Optional[int] = None,
        key_prefix: Optional[str] = None,
        exclude_args: Optional[List[str]] = None,
    ):
        """
        Cache decorator for async functions.

        Args:
            cache_type: Type of cache for TTL lookup
            ttl: Override TTL in seconds
            key_prefix: Custom key prefix
            exclude_args: Arguments to exclude from cache key
        """

        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                func_name = key_prefix or f"{func.__module__}.{func.__name__}"

                # Filter out excluded args
                filtered_kwargs = kwargs.copy()
                if exclude_args:
                    for arg in exclude_args:
                        filtered_kwargs.pop(arg, None)

                cache_key = self.cache._generate_key(
                    func_name, str(args), **filtered_kwargs
                )

                # Try to get from cache
                cached_result = await self.cache.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"Cache hit for {func_name}")
                    return cached_result

                # Execute function and cache result
                logger.debug(f"Cache miss for {func_name}, executing function")
                result = await func(*args, **kwargs)

                # Cache the result
                await self.cache.set(cache_key, result, ttl, cache_type)

                return result

            return wrapper

        return decorator


class PerformanceMonitor:
    """Performance monitoring and metrics collection."""

    def __init__(self, redis_cache: Optional[RedisCache] = None):
        self.cache = redis_cache
        self.start_time = time.time()

    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics."""
        try:
            return {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory": {
                    "total": psutil.virtual_memory().total,
                    "available": psutil.virtual_memory().available,
                    "percent": psutil.virtual_memory().percent,
                },
                "disk": {
                    "total": psutil.disk_usage("/").total,
                    "free": psutil.disk_usage("/").free,
                    "percent": psutil.disk_usage("/").percent,
                },
                "uptime_seconds": time.time() - self.start_time,
            }
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {}

    async def get_cache_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics."""
        if not self.cache:
            return {"status": "no_cache"}

        return await self.cache.health_check()

    def performance_middleware(self, request, call_next):
        """Middleware to track request performance."""

        async def wrapper():
            start_time = time.time()

            # Process request
            response = await call_next(request)

            # Calculate metrics
            process_time = time.time() - start_time

            # Add performance headers
            response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))

            # Log slow requests
            if process_time > 2.0:  # Slow request threshold
                logger.warning(
                    f"Slow request: {request.method} {request.url.path} "
                    f"took {process_time:.2f}s"
                )

            return response

        return wrapper()


# Global instances
performance_config = PerformanceConfig()
performance_monitor = PerformanceMonitor()

# Initialize cache instance (will be configured in app startup)
cache: Optional[RedisCache] = None
cache_decorator: Optional[CacheDecorator] = None


async def init_cache(redis_url: str):
    """Initialize global cache instance."""
    global cache, cache_decorator

    cache = RedisCache(redis_url)
    await cache.connect()
    cache_decorator = CacheDecorator(cache)


async def cleanup_cache():
    """Cleanup cache connections."""
    global cache

    if cache:
        await cache.disconnect()
        cache = None


# Export main components
__all__ = [
    "PerformanceConfig",
    "RedisCache",
    "DatabasePerformance",
    "CacheDecorator",
    "PerformanceMonitor",
    "performance_config",
    "performance_monitor",
    "init_cache",
    "cleanup_cache",
    "cache",
    "cache_decorator",
]
