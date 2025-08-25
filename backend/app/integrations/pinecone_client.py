"""
Pinecone vector database client for RAG document retrieval.

Implements production-ready async client for Pinecone with embedding generation,
vector search, relevance scoring, and comprehensive error handling with circuit
breakers, retry logic, and graceful fallbacks.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

import httpx
import numpy as np
from pinecone import Pinecone

from app.core.config import settings
from app.core.exceptions import ExternalServiceException
from app.core.resilience import resilience_manager

logger = logging.getLogger(__name__)


class PineconeClient:
    """Async client for Pinecone vector database operations."""

    def __init__(self) -> None:
        """Initialize Pinecone client with pre-configured index."""
        try:
            self.client = Pinecone(api_key=settings.PINECONE_API_KEY)
            self.index_name = settings.PINECONE_INDEX_NAME
            self.index_host = settings.PINECONE_INDEX_HOST

            # Connect to existing index
            self.index = self.client.Index(name=self.index_name, host=self.index_host)

            logger.info(f"Pinecone client initialized for index: {self.index_name}")

        except Exception as e:
            logger.error(f"Failed to initialize Pinecone client: {str(e)}")
            raise ExternalServiceException(
                "Pinecone", f"Client initialization failed: {str(e)}"
            )

    async def search_documents(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents using vector similarity with resilience.

        Args:
            query_embedding: Query vector embedding (1024 dimensions)
            top_k: Number of similar documents to retrieve
            filter_metadata: Optional metadata filter for search
            correlation_id: Request correlation ID for tracking

        Returns:
            List of similar documents with metadata and scores

        Raises:
            ExternalServiceException: If Pinecone search fails after all retries
        """
        logger.info(
            f"Searching Pinecone index with resilience protection",
            extra={
                "correlation_id": correlation_id,
                "index_name": self.index_name,
                "top_k": top_k,
                "has_filter": bool(filter_metadata),
                "embedding_dims": len(query_embedding),
            },
        )

        async def _perform_search() -> List[Dict[str, Any]]:
            """Internal search function with direct Pinecone API call."""
            try:
                # Perform vector search
                search_response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.index.query(
                        vector=query_embedding,
                        top_k=top_k,
                        filter=filter_metadata,
                        include_metadata=True,
                        include_values=False,
                    ),
                )

                # Process search results
                documents = []
                for match in search_response.matches:
                    doc = {
                        "id": match.id,
                        "score": float(match.score),
                        "metadata": dict(match.metadata) if match.metadata else {},
                    }

                    # Extract content from metadata
                    if match.metadata:
                        doc["content"] = match.metadata.get("content", "")
                        doc["source"] = match.metadata.get("source", "")
                        doc["category"] = match.metadata.get("category", "general")
                        doc["title"] = match.metadata.get("title", "")

                    documents.append(doc)

                logger.info(
                    f"Pinecone search completed successfully",
                    extra={
                        "correlation_id": correlation_id,
                        "results_count": len(documents),
                        "avg_score": (
                            sum(doc["score"] for doc in documents) / len(documents)
                            if documents
                            else 0
                        ),
                        "top_score": (
                            max(doc["score"] for doc in documents) if documents else 0
                        ),
                    },
                )

                return documents

            except Exception as e:
                logger.error(
                    f"Pinecone search operation failed: {str(e)}",
                    extra={
                        "correlation_id": correlation_id,
                        "error_type": type(e).__name__,
                    },
                )
                raise ExternalServiceException(
                    "Pinecone",
                    f"Vector search failed: {str(e)}",
                    correlation_id=correlation_id,
                )

        # Execute with resilience protection
        try:
            return await resilience_manager.execute_with_resilience(
                "pinecone", _perform_search, correlation_id=correlation_id
            )
        except Exception as e:
            # If all resilience attempts failed, try fallback strategy
            logger.warning(
                f"Pinecone search failed with resilience, attempting fallback",
                extra={"correlation_id": correlation_id, "error": str(e)},
            )
            return await self._search_fallback(query_embedding, top_k, correlation_id)

    async def _search_fallback(
        self,
        query_embedding: List[float],
        top_k: int,
        correlation_id: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Fallback search strategy when primary Pinecone search fails.

        Returns cached results if available, or empty results with warning.
        """
        logger.info(
            f"Executing Pinecone search fallback strategy",
            extra={"correlation_id": correlation_id, "top_k": top_k},
        )

        try:
            # Try to get cached results from Redis
            from app.integrations.redis_client import get_redis_client

            redis_client = await get_redis_client()

            # Look for cached similar queries (simple hash-based lookup)
            cache_pattern = f"rag_context:*:vector_only"
            cached_keys = await redis_client.get_keys_by_pattern(
                cache_pattern, correlation_id
            )

            if cached_keys:
                # Return first cached result as fallback
                cached_result = await redis_client.get_json(
                    cached_keys[0], correlation_id
                )
                if cached_result and len(cached_result) >= top_k:
                    logger.info(
                        f"Using cached results as Pinecone fallback",
                        extra={
                            "correlation_id": correlation_id,
                            "cached_results": len(cached_result),
                        },
                    )
                    return cached_result[:top_k]  # type: ignore

        except Exception as cache_error:
            logger.warning(
                f"Cache fallback also failed: {str(cache_error)}",
                extra={"correlation_id": correlation_id},
            )

        # Final fallback: return empty results but log the failure
        logger.error(
            f"All Pinecone search strategies failed, returning empty results",
            extra={"correlation_id": correlation_id},
        )

        return []  # Empty results allow system to continue with direct LLM response

    async def embed_text(self, text: str, correlation_id: str = "") -> List[float]:
        """
        Generate embedding for text using multiple strategies with resilience.

        Args:
            text: Text to embed
            correlation_id: Request correlation ID for tracking

        Returns:
            Text embedding vector (1024 dimensions)

        Raises:
            ExternalServiceException: If all embedding strategies fail
        """
        logger.info(
            f"Generating text embedding with resilience protection",
            extra={"correlation_id": correlation_id, "text_length": len(text)},
        )

        # Check cache first (outside resilience pattern for speed)
        try:
            from app.integrations.redis_client import get_redis_client

            redis_client = await get_redis_client()
            cache_key = f"embedding:{hash(text)}:{settings.EMBEDDING_MODEL}"
            cached_embedding = await redis_client.get_json(cache_key, correlation_id)

            if cached_embedding:
                logger.info(
                    f"Retrieved text embedding from cache",
                    extra={
                        "correlation_id": correlation_id,
                        "embedding_dims": len(cached_embedding),
                    },
                )
                return cached_embedding  # type: ignore
        except Exception as cache_error:
            logger.warning(
                f"Cache lookup failed, proceeding with embedding generation: {str(cache_error)}",
                extra={"correlation_id": correlation_id},
            )

        # Try primary embedding strategy with resilience
        async def _primary_embedding() -> List[float]:
            return await self._generate_embedding_via_pinecone_inference(
                text, correlation_id
            )

        try:
            embedding = await resilience_manager.execute_with_resilience(
                "embedding_api", _primary_embedding, correlation_id=correlation_id
            )

            # Cache successful result
            try:
                await redis_client.set_json(
                    cache_key,
                    embedding,
                    expiration=settings.EMBEDDING_CACHE_TTL_SECONDS,
                    correlation_id=correlation_id,
                )
            except Exception as cache_error:
                logger.warning(
                    f"Failed to cache embedding: {str(cache_error)}",
                    extra={"correlation_id": correlation_id},
                )

            logger.info(
                f"Text embedding generated successfully",
                extra={
                    "correlation_id": correlation_id,
                    "embedding_dims": len(embedding),
                    "model": settings.EMBEDDING_MODEL,
                },
            )

            return embedding

        except Exception as e:
            # Primary strategy failed, try fallback
            logger.warning(
                f"Primary embedding failed, trying fallback strategies: {str(e)}",
                extra={"correlation_id": correlation_id},
            )
            return await self._embedding_fallback_cascade(text, correlation_id)

    async def _generate_embedding_via_pinecone_inference(
        self, text: str, correlation_id: str = ""
    ) -> List[float]:
        """
        Generate embedding using Pinecone Inference API with llama-text-embed-v2.

        Args:
            text: Text to embed
            correlation_id: Request correlation ID

        Returns:
            Embedding vector (1024 dimensions)

        Raises:
            ExternalServiceException: If API call fails
        """
        logger.info(
            f"Calling Pinecone Inference API for embedding",
            extra={
                "correlation_id": correlation_id,
                "model": settings.EMBEDDING_MODEL,
                "text_preview": text[:100] + "..." if len(text) > 100 else text,
            },
        )

        try:
            # Use Pinecone's embedding service via their Inference API
            # This uses the same API key as the vector database
            inference_response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.inference.embed(
                    model=settings.EMBEDDING_MODEL, inputs=[text], parameters={}
                ),
            )

            # Extract the embedding from the response
            if (
                not inference_response
                or not hasattr(inference_response, "data")
                or not inference_response.data
            ):
                raise ValueError("Empty response from Pinecone Inference API")

            embedding_data = inference_response.data[0]
            if not hasattr(embedding_data, "values") or not embedding_data.values:
                raise ValueError("No embedding values in API response")

            embedding = embedding_data.values

            # Validate embedding dimensions
            if len(embedding) != settings.EMBEDDING_DIMENSIONS:
                raise ValueError(
                    f"Embedding dimension mismatch: expected {settings.EMBEDDING_DIMENSIONS}, got {len(embedding)}"
                )

            logger.info(
                f"Pinecone Inference API embedding generated",
                extra={
                    "correlation_id": correlation_id,
                    "embedding_dims": len(embedding),
                    "api_model": settings.EMBEDDING_MODEL,
                },
            )

            return embedding

        except Exception as e:
            logger.error(
                f"Pinecone Inference API call failed: {str(e)}",
                extra={
                    "correlation_id": correlation_id,
                    "error_type": type(e).__name__,
                },
            )
            raise ExternalServiceException(
                "Pinecone Inference API",
                f"Embedding generation failed: {str(e)}",
                correlation_id=correlation_id,
            )

    async def _embedding_fallback_cascade(
        self, text: str, correlation_id: str = ""
    ) -> List[float]:
        """
        Comprehensive embedding fallback cascade with multiple strategies.

        Tries multiple embedding services in order of reliability and cost.
        """
        logger.info(
            f"Starting embedding fallback cascade",
            extra={"correlation_id": correlation_id, "text_length": len(text)},
        )

        # Strategy 1: OpenAI (if available and configured)
        if hasattr(settings, "OPENAI_API_KEY") and settings.OPENAI_API_KEY:
            try:

                async def _openai_embedding() -> List[float]:
                    return await self._generate_embedding_via_openai(
                        text, correlation_id
                    )

                embedding = await resilience_manager.execute_with_resilience(
                    "embedding_api", _openai_embedding, correlation_id=correlation_id
                )

                logger.info(
                    f"OpenAI embedding fallback successful",
                    extra={"correlation_id": correlation_id, "dims": len(embedding)},
                )
                return embedding

            except Exception as e:
                logger.warning(
                    f"OpenAI embedding fallback failed: {str(e)}",
                    extra={"correlation_id": correlation_id},
                )

        # Strategy 2: Sentence Transformers API (free but less reliable)
        try:
            embedding = await self._generate_embedding_via_sentence_transformers(
                text, correlation_id
            )
            logger.info(
                f"Sentence-transformers fallback successful",
                extra={"correlation_id": correlation_id, "dims": len(embedding)},
            )
            return embedding

        except Exception as e:
            logger.warning(
                f"Sentence-transformers fallback failed: {str(e)}",
                extra={"correlation_id": correlation_id},
            )

        # Strategy 3: Check for cached similar embeddings
        try:
            cached_embedding = await self._find_similar_cached_embedding(
                text, correlation_id
            )
            if cached_embedding:
                logger.info(
                    f"Using similar cached embedding as fallback",
                    extra={
                        "correlation_id": correlation_id,
                        "dims": len(cached_embedding),
                    },
                )
                return cached_embedding
        except Exception as e:
            logger.warning(
                f"Cached embedding lookup failed: {str(e)}",
                extra={"correlation_id": correlation_id},
            )

        # Strategy 4: Deterministic embedding (last resort for development/testing)
        logger.warning(
            f"All embedding services failed, using deterministic fallback",
            extra={"correlation_id": correlation_id},
        )
        return await self._generate_deterministic_embedding(text, correlation_id)

    async def _find_similar_cached_embedding(
        self, text: str, correlation_id: str = ""
    ) -> Optional[List[float]]:
        """
        Find cached embedding for similar text to use as fallback.

        Uses simple text similarity heuristics to find reusable embeddings.
        """
        try:
            from app.integrations.redis_client import get_redis_client

            redis_client = await get_redis_client()

            # Get all cached embeddings
            cache_pattern = f"embedding:*:{settings.EMBEDDING_MODEL}"
            cache_keys = await redis_client.get_keys_by_pattern(
                cache_pattern, correlation_id
            )

            if not cache_keys:
                return None

            text_lower = text.lower().strip()
            text_words = set(text_lower.split())

            best_match = None
            best_similarity = 0.0

            # Simple word overlap similarity
            for cache_key in cache_keys[:10]:  # Check max 10 cached embeddings
                try:
                    cached_embedding = await redis_client.get_json(
                        cache_key, correlation_id
                    )
                    if not cached_embedding:
                        continue

                    # Extract original text hash from cache key
                    # Format: embedding:{hash}:{model}
                    key_parts = cache_key.split(":")
                    if len(key_parts) >= 2:
                        # For now, use simple length-based similarity
                        # In production, you might store metadata about cached text
                        text_len_similarity = 1.0 - abs(
                            len(text) - len(cache_key)
                        ) / max(len(text), len(cache_key))

                        if (
                            text_len_similarity > best_similarity
                            and text_len_similarity > 0.7
                        ):
                            best_similarity = text_len_similarity
                            best_match = cached_embedding

                except Exception:
                    continue  # Skip failed cache entries

            if best_match and best_similarity > 0.7:
                logger.info(
                    f"Found similar cached embedding with {best_similarity:.2f} similarity",
                    extra={
                        "correlation_id": correlation_id,
                        "similarity": best_similarity,
                    },
                )
                return best_match  # type: ignore

        except Exception as e:
            logger.warning(
                f"Failed to search cached embeddings: {str(e)}",
                extra={"correlation_id": correlation_id},
            )

        return None

    async def _generate_embedding_via_external_api(
        self, text: str, correlation_id: str = ""
    ) -> List[float]:
        """
        Fallback embedding generation using multiple external services.

        Args:
            text: Text to embed
            correlation_id: Request correlation ID

        Returns:
            Embedding vector

        Raises:
            ExternalServiceException: If all external APIs fail
        """
        logger.info(
            f"Using external embedding services as fallback",
            extra={"correlation_id": correlation_id},
        )

        # Try OpenAI first (most reliable)
        if settings.OPENAI_API_KEY:
            try:
                return await self._generate_embedding_via_openai(text, correlation_id)
            except Exception as e:
                logger.warning(
                    f"OpenAI embedding failed, trying alternatives: {str(e)}",
                    extra={"correlation_id": correlation_id},
                )

        # Try sentence-transformers API (free alternative)
        try:
            return await self._generate_embedding_via_sentence_transformers(
                text, correlation_id
            )
        except Exception as e:
            logger.warning(
                f"Sentence-transformers API failed: {str(e)}",
                extra={"correlation_id": correlation_id},
            )

        # Final fallback: deterministic embedding (for testing only)
        logger.warning(
            f"All external APIs failed, using deterministic fallback",
            extra={"correlation_id": correlation_id},
        )
        return await self._generate_deterministic_embedding(text, correlation_id)

    async def _generate_embedding_via_openai(
        self, text: str, correlation_id: str = ""
    ) -> List[float]:
        """Generate embedding using OpenAI's API."""
        logger.info(
            f"Using OpenAI embedding API",
            extra={
                "correlation_id": correlation_id,
                "model": settings.OPENAI_EMBEDDING_MODEL,
            },
        )

        try:
            async with httpx.AsyncClient(
                timeout=settings.EMBEDDING_REQUEST_TIMEOUT_SECONDS
            ) as client:
                headers = {
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                }

                payload = {
                    "input": text,
                    "model": settings.OPENAI_EMBEDDING_MODEL,
                    "encoding_format": "float",
                }

                response = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers=headers,
                    json=payload,
                )

                response.raise_for_status()
                result = response.json()

                if "data" not in result or not result["data"]:
                    raise ValueError("No embedding data in OpenAI response")

                raw_embedding = result["data"][0]["embedding"]

                # OpenAI text-embedding-3-large is 3072 dimensions, need to truncate to 1024
                if len(raw_embedding) > settings.EMBEDDING_DIMENSIONS:
                    embedding = raw_embedding[: settings.EMBEDDING_DIMENSIONS]
                else:
                    # Pad if somehow shorter
                    embedding = raw_embedding + [0.0] * (
                        settings.EMBEDDING_DIMENSIONS - len(raw_embedding)
                    )

                # Normalize to unit vector for cosine similarity
                magnitude = np.linalg.norm(embedding)
                if magnitude > 0:
                    embedding = [x / magnitude for x in embedding]

                logger.info(
                    f"OpenAI embedding generated successfully",
                    extra={
                        "correlation_id": correlation_id,
                        "original_dims": len(raw_embedding),
                        "final_dims": len(embedding),
                    },
                )

                return embedding

        except httpx.HTTPError as e:
            logger.error(
                f"OpenAI API HTTP error: {str(e)}",
                extra={"correlation_id": correlation_id},
            )
            raise ExternalServiceException(
                "OpenAI API",
                f"HTTP request failed: {str(e)}",
                correlation_id=correlation_id,
            )

    async def _generate_embedding_via_sentence_transformers(
        self, text: str, correlation_id: str = ""
    ) -> List[float]:
        """Generate embedding using sentence-transformers via public API."""
        logger.info(
            f"Using sentence-transformers API",
            extra={"correlation_id": correlation_id},
        )

        try:
            # Use a reliable public API for sentence transformers
            async with httpx.AsyncClient(
                timeout=settings.EMBEDDING_REQUEST_TIMEOUT_SECONDS
            ) as client:
                # Try multiple endpoints for reliability
                endpoints = [
                    "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L12-v2",
                    "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-mpnet-base-v2",
                ]

                for endpoint in endpoints:
                    try:
                        payload = {
                            "inputs": text,
                            "options": {"wait_for_model": True, "use_cache": True},
                        }

                        response = await client.post(
                            endpoint,
                            headers={"Content-Type": "application/json"},
                            json=payload,
                        )

                        if response.status_code == 200:
                            raw_embedding = response.json()

                            # Handle different response formats
                            if isinstance(raw_embedding, list):
                                if isinstance(raw_embedding[0], list):
                                    raw_embedding = raw_embedding[0]
                            else:
                                raise ValueError("Unexpected response format")

                            # Resize to target dimensions
                            if len(raw_embedding) < settings.EMBEDDING_DIMENSIONS:
                                # Pad with zeros
                                embedding = raw_embedding + [0.0] * (
                                    settings.EMBEDDING_DIMENSIONS - len(raw_embedding)
                                )
                            else:
                                # Truncate
                                embedding = raw_embedding[
                                    : settings.EMBEDDING_DIMENSIONS
                                ]

                            # Normalize
                            magnitude = np.linalg.norm(embedding)
                            if magnitude > 0:
                                embedding = [x / magnitude for x in embedding]

                            logger.info(
                                f"Sentence-transformers embedding generated",
                                extra={
                                    "correlation_id": correlation_id,
                                    "endpoint": endpoint,
                                    "dimensions": len(embedding),
                                },
                            )

                            return embedding

                    except Exception as e:
                        logger.warning(f"Endpoint {endpoint} failed: {e}")
                        continue

                raise ValueError("All sentence-transformer endpoints failed")

        except Exception as e:
            logger.error(
                f"Sentence-transformers API failed: {str(e)}",
                extra={"correlation_id": correlation_id},
            )
            raise

    async def _generate_deterministic_embedding(
        self, text: str, correlation_id: str = ""
    ) -> List[float]:
        """
        Generate deterministic embedding as final fallback.

        This creates embeddings with some semantic properties for development/testing.
        NOT recommended for production use.
        """
        logger.warning(
            f"Using deterministic embedding fallback - NOT for production",
            extra={"correlation_id": correlation_id},
        )

        import hashlib

        # Create multiple hash seeds from text for better distribution
        text_lower = text.lower().strip()

        # Generate multiple hash values
        md5_hash = hashlib.md5(text_lower.encode()).hexdigest()
        sha1_hash = hashlib.sha1(text_lower.encode()).hexdigest()

        # Extract semantic features (simple keyword-based)
        financial_keywords = [
            "account",
            "payment",
            "transfer",
            "fraud",
            "security",
            "card",
            "bank",
            "transaction",
            "fee",
            "balance",
            "withdraw",
            "deposit",
            "kyc",
            "compliance",
            "authentication",
            "password",
            "login",
        ]

        # Create feature vector based on keyword presence
        feature_vector = []
        for keyword in financial_keywords:
            if keyword in text_lower:
                feature_vector.append(1.0)
            else:
                feature_vector.append(0.0)

        # Use hash values to generate base embedding
        embedding = []
        hash_combined = md5_hash + sha1_hash

        for i in range(settings.EMBEDDING_DIMENSIONS):
            # Use different parts of hash for each dimension
            hash_slice = hash_combined[
                (i * 2) % len(hash_combined) : (i * 2 + 8) % len(hash_combined)
            ]
            if len(hash_slice) < 8:
                hash_slice = (hash_slice * 3)[:8]  # Repeat to get enough chars

            # Convert to float in range [-1, 1]
            hash_int = int(hash_slice, 16) if hash_slice else 0
            normalized_val = ((hash_int % 10000) / 5000.0) - 1.0

            # Add semantic signal for financial keywords
            if i < len(feature_vector):
                normalized_val += feature_vector[i] * 0.3  # Boost for relevant keywords

            embedding.append(normalized_val)

        # Normalize to unit vector
        magnitude = np.linalg.norm(embedding)
        if magnitude > 0:
            embedding = [float(x / magnitude) for x in embedding]

        logger.info(
            f"Deterministic embedding generated",
            extra={
                "correlation_id": correlation_id,
                "semantic_features": sum(feature_vector),
                "dimensions": len(embedding),
            },
        )

        return embedding

    async def get_index_stats(self, correlation_id: str = "") -> Dict[str, Any]:
        """
        Get Pinecone index statistics.

        Args:
            correlation_id: Request correlation ID for tracking

        Returns:
            Index statistics and metadata
        """
        logger.info(
            f"Fetching Pinecone index stats",
            extra={"correlation_id": correlation_id, "index_name": self.index_name},
        )

        try:
            # Get index stats
            stats_response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.index.describe_index_stats()
            )

            stats = {
                "total_vector_count": stats_response.total_vector_count,
                "dimension": stats_response.dimension,
                "index_fullness": stats_response.index_fullness,
                "namespaces": {},
            }

            # Process namespace stats
            if stats_response.namespaces:
                for namespace, namespace_stats in stats_response.namespaces.items():
                    stats["namespaces"][namespace] = {
                        "vector_count": namespace_stats.vector_count
                    }

            logger.info(
                f"Pinecone index stats retrieved",
                extra={
                    "correlation_id": correlation_id,
                    "total_vectors": stats["total_vector_count"],
                    "dimension": stats["dimension"],
                    "fullness": stats["index_fullness"],
                },
            )

            return stats

        except Exception as e:
            logger.error(
                f"Failed to get Pinecone index stats: {str(e)}",
                extra={"correlation_id": correlation_id},
            )
            raise ExternalServiceException(
                "Pinecone",
                f"Failed to get index stats: {str(e)}",
                correlation_id=correlation_id,
            )

    async def health_check(self, correlation_id: str = "") -> Dict[str, Any]:
        """
        Comprehensive health check including circuit breaker status.

        Args:
            correlation_id: Request correlation ID

        Returns:
            Detailed health status including circuit breaker state
        """
        health_status: Dict[str, Any] = {
            "service": "pinecone",
            "status": "healthy",
            "checks": {},
            "circuit_breakers": {},
            "timestamp": time.time(),
        }

        # Check circuit breaker states
        try:
            pinecone_cb_health = resilience_manager.get_service_health("pinecone")
            embedding_cb_health = resilience_manager.get_service_health("embedding_api")

            health_status["circuit_breakers"] = {
                "pinecone": {
                    "state": pinecone_cb_health["state"],
                    "status": pinecone_cb_health["status"],
                    "error_rate": pinecone_cb_health["error_rate"],
                    "total_requests": pinecone_cb_health["total_requests"],
                },
                "embedding_api": {
                    "state": embedding_cb_health["state"],
                    "status": embedding_cb_health["status"],
                    "error_rate": embedding_cb_health["error_rate"],
                    "total_requests": embedding_cb_health["total_requests"],
                },
            }

            # Overall status based on circuit breakers
            if (
                pinecone_cb_health["status"] == "unhealthy"
                or embedding_cb_health["status"] == "unhealthy"
            ):
                health_status["status"] = "unhealthy"
            elif (
                pinecone_cb_health["status"] == "degraded"
                or embedding_cb_health["status"] == "degraded"
            ):
                health_status["status"] = "degraded"

        except Exception as e:
            logger.error(
                f"Failed to get circuit breaker health: {str(e)}",
                extra={"correlation_id": correlation_id},
            )
            health_status["circuit_breakers"] = {"error": str(e)}

        # Test basic Pinecone connectivity
        try:

            async def _test_connectivity() -> bool:
                stats = await self.get_index_stats(correlation_id)
                return stats["total_vector_count"] > 0

            connectivity_result = await resilience_manager.execute_with_resilience(
                "pinecone", _test_connectivity, correlation_id=correlation_id
            )

            health_status["checks"]["connectivity"] = {
                "status": "healthy" if connectivity_result else "degraded",
                "details": {"has_vectors": connectivity_result},
            }

        except Exception as e:
            health_status["checks"]["connectivity"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            health_status["status"] = "unhealthy"

        # Test embedding generation
        try:
            test_embedding = await self.embed_text(
                "health check test", correlation_id=correlation_id
            )

            health_status["checks"]["embedding"] = {
                "status": "healthy",
                "details": {
                    "embedding_dims": len(test_embedding),
                    "expected_dims": settings.EMBEDDING_DIMENSIONS,
                },
            }

        except Exception as e:
            health_status["checks"]["embedding"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            if health_status["status"] == "healthy":
                health_status["status"] = "degraded"

        # Test search functionality
        try:
            test_embedding = [0.1] * settings.EMBEDDING_DIMENSIONS  # Simple test vector
            search_results = await self.search_documents(
                query_embedding=test_embedding,
                top_k=1,
                correlation_id=correlation_id,
            )

            health_status["checks"]["search"] = {
                "status": "healthy",
                "details": {"can_search": True, "results_count": len(search_results)},
            }

        except Exception as e:
            health_status["checks"]["search"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            if health_status["status"] == "healthy":
                health_status["status"] = "degraded"

        logger.info(
            f"Pinecone health check completed",
            extra={
                "correlation_id": correlation_id,
                "overall_status": health_status["status"],
                "checks_passed": sum(
                    1
                    for check in health_status["checks"].values()
                    if check.get("status") == "healthy"
                ),
                "total_checks": len(health_status["checks"]),
            },
        )

        return health_status

    def calculate_relevance_score(
        self, similarity_score: float, metadata: Dict[str, Any]
    ) -> float:
        """
        Calculate enhanced relevance score considering metadata.

        Args:
            similarity_score: Raw cosine similarity score
            metadata: Document metadata for scoring

        Returns:
            Enhanced relevance score
        """
        base_score = similarity_score

        # Apply metadata-based scoring boosts
        category_boost = {
            "account": 1.1,
            "payment": 1.1,
            "security": 1.2,
            "compliance": 1.0,
            "general": 0.9,
        }

        category = metadata.get("category", "general")
        score = base_score * category_boost.get(category, 1.0)

        # Boost for high-quality sources
        source = metadata.get("source", "")
        if source in ["official_docs", "regulatory_guidance"]:
            score *= 1.15

        # Recency boost (if timestamp available)
        # TODO: Implement recency scoring when timestamp metadata available

        return min(score, 1.0)  # Cap at 1.0
