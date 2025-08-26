"""
Response caching service for common queries with deduplication.

Implements intelligent caching for frequently asked questions and query
deduplication to improve response times and reduce computational overhead.
"""

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from app.integrations.redis_client import RedisClient, get_redis_client

logger = logging.getLogger(__name__)


class ResponseCacheService:
    """Service for caching responses and deduplicating queries."""

    def __init__(self) -> None:
        """Initialize response cache service."""
        self.redis_client: Optional[RedisClient] = None  # Will be initialized async
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "deduplicated": 0,
            "cached_responses": 0,
        }

        # Configuration
        self.default_ttl = 3600  # 1 hour default cache TTL
        self.common_query_ttl = 86400  # 24 hours for common queries
        self.deduplication_window = 300  # 5 minutes for query deduplication
        self.similarity_threshold = 0.85  # Threshold for query similarity

        # In-memory deduplication tracking
        self.pending_queries: Dict[str, asyncio.Event] = {}
        self.query_results: Dict[str, Tuple[str, Dict[str, Any]]] = {}

        logger.info("Response cache service initialized with Redis backend")

    async def _ensure_redis_client(self) -> None:
        """Ensure Redis client is initialized."""
        if self.redis_client is None:
            try:
                self.redis_client = await get_redis_client()
            except Exception as e:
                logger.warning(f"Failed to initialize Redis client: {e}")
                # Continue without Redis (graceful degradation)

    def _generate_cache_key(self, query: str, context_hash: str = "") -> str:
        """
        Generate cache key for query with optional context.

        Args:
            query: User query text
            context_hash: Optional hash of RAG context

        Returns:
            Cache key string
        """
        # Normalize query for better cache hits
        normalized_query = query.lower().strip()

        # Create hash of query + context
        content = f"{normalized_query}:{context_hash}"
        query_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        return f"response_cache:{query_hash}"

    def _generate_query_hash(self, query: str, user_id: Optional[str] = None) -> str:
        """
        Generate hash for query deduplication.

        Args:
            query: User query text
            user_id: Optional user identifier

        Returns:
            Query hash for deduplication
        """
        # Normalize query
        normalized_query = query.lower().strip()

        # Include user_id for user-specific deduplication
        content = f"{normalized_query}:{user_id or 'anonymous'}"
        return hashlib.sha256(content.encode()).hexdigest()[:12]

    async def _calculate_query_similarity(self, query1: str, query2: str) -> float:
        """
        Calculate similarity between two queries using simple text similarity.

        Args:
            query1: First query
            query2: Second query

        Returns:
            Similarity score between 0 and 1
        """
        # Simple Jaccard similarity for quick comparison
        words1 = set(query1.lower().split())
        words2 = set(query2.lower().split())

        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)

    async def get_cached_response(
        self,
        query: str,
        context_docs: Optional[List[Dict[str, Any]]] = None,
        correlation_id: str = "",
    ) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Get cached response for query if available.

        Args:
            query: User query
            context_docs: Optional RAG context documents
            correlation_id: Request correlation ID

        Returns:
            Cached response and metadata if found, None otherwise
        """
        try:
            # Generate context hash from documents
            context_hash = ""
            if context_docs:
                context_content = json.dumps(
                    [
                        {
                            "id": doc.get("id", ""),
                            "confidence": doc.get("confidence", 0),
                        }
                        for doc in context_docs[:3]  # Use top 3 for hash
                    ],
                    sort_keys=True,
                )
                context_hash = hashlib.sha256(context_content.encode()).hexdigest()[:8]

            cache_key = self._generate_cache_key(query, context_hash)

            # Ensure Redis client is initialized
            await self._ensure_redis_client()
            if not self.redis_client:
                return None

            # Try to get from cache
            cached_data = await self.redis_client.get_json(cache_key, correlation_id)

            if cached_data:
                self.cache_stats["hits"] += 1

                logger.info(
                    f"Cache hit for query",
                    extra={
                        "correlation_id": correlation_id,
                        "cache_key": cache_key,
                        "response_length": len(cached_data.get("response", "")),
                    },
                )

                # Update access timestamp
                cached_data["last_accessed"] = time.time()
                await self.redis_client.set_json(
                    cache_key,
                    cached_data,
                    expiration=self.default_ttl,
                    correlation_id=correlation_id,
                )

                return cached_data["response"], cached_data.get("metadata", {})

            self.cache_stats["misses"] += 1
            return None

        except Exception as e:
            logger.error(
                f"Failed to get cached response: {str(e)}",
                extra={"correlation_id": correlation_id},
            )
            return None

    async def cache_response(
        self,
        query: str,
        response: str,
        metadata: Dict[str, Any],
        context_docs: Optional[List[Dict[str, Any]]] = None,
        is_common_query: bool = False,
        correlation_id: str = "",
    ) -> bool:
        """
        Cache response for future use.

        Args:
            query: Original user query
            response: Generated response
            metadata: Response metadata
            context_docs: RAG context documents
            is_common_query: Whether this is a common/frequent query
            correlation_id: Request correlation ID

        Returns:
            True if cached successfully, False otherwise
        """
        try:
            # Generate context hash
            context_hash = ""
            if context_docs:
                context_content = json.dumps(
                    [
                        {
                            "id": doc.get("id", ""),
                            "confidence": doc.get("confidence", 0),
                        }
                        for doc in context_docs[:3]
                    ],
                    sort_keys=True,
                )
                context_hash = hashlib.sha256(context_content.encode()).hexdigest()[:8]

            cache_key = self._generate_cache_key(query, context_hash)

            # Ensure Redis client is initialized
            await self._ensure_redis_client()
            if not self.redis_client:
                return False

            # Prepare cache data
            cache_data = {
                "query": query,
                "response": response,
                "metadata": metadata,
                "context_hash": context_hash,
                "cached_at": time.time(),
                "last_accessed": time.time(),
                "access_count": 1,
                "is_common": is_common_query,
            }

            # Set TTL based on query type
            ttl = self.common_query_ttl if is_common_query else self.default_ttl

            # Cache the response
            success = await self.redis_client.set_json(
                cache_key, cache_data, expiration=ttl, correlation_id=correlation_id
            )

            if success:
                self.cache_stats["cached_responses"] += 1

                logger.info(
                    f"Response cached successfully",
                    extra={
                        "correlation_id": correlation_id,
                        "cache_key": cache_key,
                        "ttl": ttl,
                        "is_common": is_common_query,
                        "response_length": len(response),
                    },
                )

            return success

        except Exception as e:
            logger.error(
                f"Failed to cache response: {str(e)}",
                extra={"correlation_id": correlation_id},
            )
            return False

    async def deduplicate_query(
        self,
        query: str,
        user_id: Optional[str] = None,
        correlation_id: str = "",
    ) -> Optional[Tuple[str, asyncio.Event]]:
        """
        Check if query is already being processed (deduplication).

        Args:
            query: User query
            user_id: Optional user identifier
            correlation_id: Request correlation ID

        Returns:
            Tuple of (query_hash, event) if query is being processed, None otherwise
        """
        try:
            query_hash = self._generate_query_hash(query, user_id)

            # Check if query is already being processed
            if query_hash in self.pending_queries:
                self.cache_stats["deduplicated"] += 1

                logger.info(
                    f"Query deduplication - waiting for existing query",
                    extra={
                        "correlation_id": correlation_id,
                        "query_hash": query_hash,
                        "user_id": user_id,
                    },
                )

                return query_hash, self.pending_queries[query_hash]

            # Mark query as being processed
            event = asyncio.Event()
            self.pending_queries[query_hash] = event

            # Schedule cleanup
            asyncio.create_task(
                self._cleanup_pending_query(query_hash, self.deduplication_window)
            )

            return None

        except Exception as e:
            logger.error(
                f"Failed to deduplicate query: {str(e)}",
                extra={"correlation_id": correlation_id},
            )
            return None

    async def complete_query_processing(
        self,
        query: str,
        response: str,
        metadata: Dict[str, Any],
        user_id: Optional[str] = None,
        correlation_id: str = "",
    ) -> None:
        """
        Mark query as completed and notify waiting requests.

        Args:
            query: Original query
            response: Generated response
            metadata: Response metadata
            user_id: Optional user identifier
            correlation_id: Request correlation ID
        """
        try:
            query_hash = self._generate_query_hash(query, user_id)

            # Store result for waiting requests
            self.query_results[query_hash] = (response, metadata)

            # Notify waiting requests
            if query_hash in self.pending_queries:
                event = self.pending_queries[query_hash]
                event.set()

                logger.info(
                    f"Query processing completed - notified waiting requests",
                    extra={
                        "correlation_id": correlation_id,
                        "query_hash": query_hash,
                        "response_length": len(response),
                    },
                )

        except Exception as e:
            logger.error(
                f"Failed to complete query processing: {str(e)}",
                extra={"correlation_id": correlation_id},
            )

    async def get_deduplicated_result(
        self,
        query_hash: str,
        timeout: float = 30.0,
        correlation_id: str = "",
    ) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Get result from deduplicated query processing.

        Args:
            query_hash: Query hash from deduplication
            timeout: Maximum wait time in seconds
            correlation_id: Request correlation ID

        Returns:
            Response and metadata if available, None on timeout
        """
        try:
            # Wait for query to complete
            if query_hash in self.pending_queries:
                event = self.pending_queries[query_hash]
                await asyncio.wait_for(event.wait(), timeout=timeout)

            # Get result
            if query_hash in self.query_results:
                result = self.query_results[query_hash]

                logger.info(
                    f"Retrieved deduplicated query result",
                    extra={
                        "correlation_id": correlation_id,
                        "query_hash": query_hash,
                        "response_length": len(result[0]),
                    },
                )

                return result

            return None

        except asyncio.TimeoutError:
            logger.warning(
                f"Deduplicated query timed out",
                extra={"correlation_id": correlation_id, "query_hash": query_hash},
            )
            return None
        except Exception as e:
            logger.error(
                f"Failed to get deduplicated result: {str(e)}",
                extra={"correlation_id": correlation_id},
            )
            return None

    async def _cleanup_pending_query(self, query_hash: str, delay: float) -> None:
        """Clean up pending query after delay."""
        await asyncio.sleep(delay)

        # Remove from pending queries
        self.pending_queries.pop(query_hash, None)

        # Remove result after additional delay
        await asyncio.sleep(delay)
        self.query_results.pop(query_hash, None)

    async def identify_common_queries(
        self,
        min_frequency: int = 5,
        time_window_hours: int = 24,
        correlation_id: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Identify common queries based on cache access patterns.

        Args:
            min_frequency: Minimum access frequency to be considered common
            time_window_hours: Time window for frequency analysis
            correlation_id: Request correlation ID

        Returns:
            List of common query patterns
        """
        try:
            # This would analyze cache access patterns
            # For now, return predefined common queries
            common_queries = [
                {
                    "pattern": "account balance",
                    "frequency": 15,
                    "cache_key_pattern": "response_cache:*balance*",
                },
                {
                    "pattern": "transaction history",
                    "frequency": 12,
                    "cache_key_pattern": "response_cache:*transaction*",
                },
                {
                    "pattern": "payment methods",
                    "frequency": 10,
                    "cache_key_pattern": "response_cache:*payment*",
                },
                {
                    "pattern": "security settings",
                    "frequency": 8,
                    "cache_key_pattern": "response_cache:*security*",
                },
            ]

            logger.info(
                f"Identified {len(common_queries)} common query patterns",
                extra={"correlation_id": correlation_id},
            )

            return common_queries

        except Exception as e:
            logger.error(
                f"Failed to identify common queries: {str(e)}",
                extra={"correlation_id": correlation_id},
            )
            return []

    async def get_cache_stats(self, correlation_id: str = "") -> Dict[str, Any]:
        """
        Get cache performance statistics.

        Args:
            correlation_id: Request correlation ID

        Returns:
            Cache statistics
        """
        try:
            total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
            hit_rate = (
                self.cache_stats["hits"] / total_requests if total_requests > 0 else 0.0
            )

            # Get Redis cache info if available
            redis_info: Dict[str, Any] = {}
            try:
                await self._ensure_redis_client()
                if self.redis_client:
                    # Get basic Redis info - no specific cache info method available
                    redis_info = {
                        "connected": True,
                        "mock_mode": self.redis_client._mock_mode,
                    }
            except Exception:
                pass  # Redis info not available

            stats = {
                "cache_hits": self.cache_stats["hits"],
                "cache_misses": self.cache_stats["misses"],
                "hit_rate": hit_rate,
                "deduplicated_queries": self.cache_stats["deduplicated"],
                "cached_responses": self.cache_stats["cached_responses"],
                "pending_queries": len(self.pending_queries),
                "stored_results": len(self.query_results),
                "redis_info": redis_info,
            }

            logger.info(
                f"Cache statistics retrieved",
                extra={
                    "correlation_id": correlation_id,
                    "hit_rate": hit_rate,
                    "total_requests": total_requests,
                },
            )

            return stats

        except Exception as e:
            logger.error(
                f"Failed to get cache stats: {str(e)}",
                extra={"correlation_id": correlation_id},
            )
            return {"error": str(e)}

    async def invalidate_cache(
        self,
        pattern: Optional[str] = None,
        correlation_id: str = "",
    ) -> int:
        """
        Invalidate cached responses by pattern.

        Args:
            pattern: Cache key pattern to invalidate (default: all)
            correlation_id: Request correlation ID

        Returns:
            Number of keys invalidated
        """
        try:
            if pattern:
                keys_pattern = f"response_cache:*{pattern}*"
            else:
                keys_pattern = "response_cache:*"

            # This would use Redis SCAN to find and delete matching keys
            # For now, return a placeholder count
            invalidated_count = 0

            logger.info(
                f"Cache invalidation completed",
                extra={
                    "correlation_id": correlation_id,
                    "pattern": pattern,
                    "invalidated_count": invalidated_count,
                },
            )

            return invalidated_count

        except Exception as e:
            logger.error(
                f"Failed to invalidate cache: {str(e)}",
                extra={"correlation_id": correlation_id},
            )
            return 0

    async def health_check(self, correlation_id: str = "") -> Dict[str, Any]:
        """
        Perform health check of response cache service.

        Args:
            correlation_id: Request correlation ID

        Returns:
            Health check results
        """
        health_status: Dict[str, Any] = {
            "service": "response_cache_service",
            "status": "healthy",
            "checks": {},
        }

        try:
            # Check Redis connectivity
            await self._ensure_redis_client()
            redis_healthy = (
                await self.redis_client.health_check() if self.redis_client else False
            )
            health_status["checks"]["redis"] = {
                "status": "healthy" if redis_healthy else "unhealthy"
            }

            if not redis_healthy:
                health_status["status"] = "degraded"

            # Check cache performance
            stats = await self.get_cache_stats(correlation_id)
            health_status["checks"]["cache_performance"] = {
                "status": "healthy",
                "hit_rate": stats.get("hit_rate", 0.0),
                "total_cached": stats.get("cached_responses", 0),
            }

            # Check deduplication system
            health_status["checks"]["deduplication"] = {
                "status": "healthy",
                "pending_queries": len(self.pending_queries),
                "stored_results": len(self.query_results),
            }

        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)

        logger.info(
            f"Response cache service health check completed",
            extra={
                "correlation_id": correlation_id,
                "status": health_status["status"],
            },
        )

        return health_status
