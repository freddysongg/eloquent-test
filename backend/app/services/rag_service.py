"""
RAG (Retrieval-Augmented Generation) service for document retrieval.

Implements complete RAG pipeline with Pinecone vector search,
embedding generation, and context optimization for AI responses.
"""

import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, cast

from app.integrations.pinecone_client import PineconeClient
from app.integrations.redis_client import RedisClient, get_redis_client
from app.services.hybrid_search_service import HybridSearchService

logger = logging.getLogger(__name__)


class RAGService:
    """Service for RAG pipeline operations with Pinecone and context management."""

    def __init__(self) -> None:
        """Initialize RAG service with optimized caching and fast retrieval."""
        self.pinecone_client = PineconeClient()
        self.hybrid_search = HybridSearchService(
            vector_weight=0.7,  # 70% vector similarity
            keyword_weight=0.3,  # 30% keyword matching
            diversity_threshold=0.85,
            max_context_tokens=8000,
        )
        self._index_initialized = False
        self._redis_client: Optional[RedisClient] = None

        # Caching configuration
        self.cache_ttl = 3600  # 1 hour cache for query results
        self.fast_cache_ttl = 300  # 5 minute cache for frequently accessed results
        self.embedding_cache_ttl = 7200  # 2 hour cache for embeddings

        # Performance tracking
        self.retrieval_times: List[float] = []
        self.cache_hit_count = 0
        self.cache_miss_count = 0

        logger.info(
            "RAG service initialized with optimized caching and performance tracking"
        )

    async def get_redis_client(self) -> Optional[Any]:
        """Get Redis client for caching (lazy initialization)."""
        if self._redis_client is None:
            try:
                self._redis_client = await get_redis_client()
            except Exception as e:
                logger.warning(f"Failed to initialize Redis client: {str(e)}")
                self._redis_client = None
        return self._redis_client

    def _generate_cache_key(self, query: str, top_k: int, use_hybrid: bool) -> str:
        """Generate cache key for query results."""
        query_hash = hashlib.md5(query.lower().strip().encode()).hexdigest()
        return f"rag:query:{query_hash}:{top_k}:{'hybrid' if use_hybrid else 'vector'}"

    def _generate_embedding_cache_key(self, text: str) -> str:
        """Generate cache key for embeddings."""
        text_hash = hashlib.md5(text.lower().strip().encode()).hexdigest()
        return f"rag:embedding:{text_hash}"

    async def retrieve_context(
        self,
        query: str,
        top_k: int = 5,
        correlation_id: str = "",
        use_hybrid_search: bool = True,
        use_cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context documents from Pinecone.

        Args:
            query: User query for semantic search
            top_k: Number of documents to retrieve
            correlation_id: Request correlation ID
            use_hybrid_search: Whether to use hybrid search (default: True)
            use_cache: Whether to use Redis caching for faster retrieval

        Returns:
            List of relevant document chunks with metadata
        """
        start_time = time.time()

        logger.info(
            f"Retrieving context with optimized pipeline",
            extra={
                "correlation_id": correlation_id,
                "query_length": len(query),
                "top_k": top_k,
                "use_cache": use_cache,
                "use_hybrid": use_hybrid_search,
            },
        )

        try:
            # Check cache first if enabled
            if use_cache:
                cache_hit = await self._try_cache_retrieval(
                    query, top_k, use_hybrid_search, correlation_id
                )
                if cache_hit:
                    retrieval_time = time.time() - start_time
                    self.retrieval_times.append(retrieval_time)
                    self.cache_hit_count += 1

                    logger.info(
                        f"Retrieved context from cache",
                        extra={
                            "correlation_id": correlation_id,
                            "retrieval_time_ms": round(retrieval_time * 1000, 2),
                            "cache_hit_rate": self.cache_hit_count
                            / (self.cache_hit_count + self.cache_miss_count),
                        },
                    )
                    return cache_hit

            self.cache_miss_count += 1

            # Parallel execution of embedding generation and index initialization
            embedding_task = self._get_cached_embedding(query, correlation_id)

            # Initialize hybrid search index if needed (separate task)
            init_task = None
            if use_hybrid_search and not self._index_initialized:
                init_task = self._initialize_hybrid_search_index(correlation_id)

            # Execute embedding task and init task in parallel if needed
            if init_task:
                results = await asyncio.gather(
                    embedding_task, init_task, return_exceptions=True
                )
                query_embedding_result = results[0]
            else:
                query_embedding_result = await embedding_task

            if isinstance(query_embedding_result, Exception):
                raise query_embedding_result

            # Type cast - we know it's List[float] after exception check
            query_embedding = cast(List[float], query_embedding_result)

            # Search Pinecone for similar documents
            documents = await self.pinecone_client.search_documents(
                query_embedding=query_embedding,
                top_k=top_k,
                correlation_id=correlation_id,
            )

            # Initialize hybrid search index if not already done
            if use_hybrid_search and not self._index_initialized:
                await self._initialize_hybrid_search_index(correlation_id)

            # Apply enhanced scoring and hybrid search
            if use_hybrid_search:
                # Use hybrid search for optimal results
                enhanced_documents = self.hybrid_search.search(
                    query=query,
                    vector_results=documents,
                    top_k=top_k * 2,  # Get more for diversity filtering
                    correlation_id=correlation_id,
                )
            else:
                # Fallback to vector-only scoring
                enhanced_documents = []
                for doc in documents:
                    enhanced_score = self.pinecone_client.calculate_relevance_score(
                        doc["score"], doc.get("metadata", {})
                    )

                    enhanced_doc = {
                        **doc,
                        "enhanced_score": enhanced_score,
                        "relevance_tier": self._get_relevance_tier(enhanced_score),
                    }

                    enhanced_documents.append(enhanced_doc)

                # Sort by enhanced score
                enhanced_documents.sort(key=lambda x: x["enhanced_score"], reverse=True)

            # Limit to requested top_k
            final_documents = enhanced_documents[:top_k]

            # Cache results asynchronously
            if use_cache:
                asyncio.create_task(
                    self._cache_results(
                        query, top_k, use_hybrid_search, final_documents, correlation_id
                    )
                )

            # Track performance metrics
            retrieval_time = time.time() - start_time
            self.retrieval_times.append(retrieval_time)

            logger.info(
                f"Context retrieval completed with optimization",
                extra={
                    "correlation_id": correlation_id,
                    "search_type": "hybrid" if use_hybrid_search else "vector_only",
                    "documents_found": len(final_documents),
                    "retrieval_time_ms": round(retrieval_time * 1000, 2),
                    "cache_hit_rate": (
                        self.cache_hit_count
                        / (self.cache_hit_count + self.cache_miss_count)
                        if (self.cache_hit_count + self.cache_miss_count) > 0
                        else 0
                    ),
                    "avg_score": (
                        sum(
                            doc.get(
                                (
                                    "hybrid_score"
                                    if use_hybrid_search
                                    else "enhanced_score"
                                ),
                                0,
                            )
                            for doc in final_documents
                        )
                        / len(final_documents)
                        if final_documents
                        else 0
                    ),
                    "avg_confidence": (
                        sum(doc.get("confidence", 0) for doc in final_documents)
                        / len(final_documents)
                        if final_documents and use_hybrid_search
                        else None
                    ),
                },
            )

            return final_documents

        except Exception as e:
            logger.error(
                f"Context retrieval failed: {str(e)}",
                extra={"correlation_id": correlation_id},
            )
            # Return empty list on failure rather than raising
            return []

    async def _try_cache_retrieval(
        self, query: str, top_k: int, use_hybrid: bool, correlation_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Try to retrieve results from cache."""
        try:
            redis_client = await self.get_redis_client()
            if not redis_client:
                return None

            cache_key = self._generate_cache_key(query, top_k, use_hybrid)
            cached_results = await redis_client.get_json(cache_key, correlation_id)

            if cached_results and "documents" in cached_results:
                return cached_results["documents"]
            return None

        except Exception as e:
            logger.warning(
                f"Cache retrieval failed: {str(e)}",
                extra={"correlation_id": correlation_id},
            )
            return None

    async def _get_cached_embedding(
        self, text: str, correlation_id: str
    ) -> List[float]:
        """Get embedding from cache or generate new one."""
        try:
            redis_client = await self.get_redis_client()

            if redis_client:
                cache_key = self._generate_embedding_cache_key(text)
                cached_embedding = await redis_client.get_json(
                    cache_key, correlation_id
                )

                if cached_embedding and "embedding" in cached_embedding:
                    return cached_embedding["embedding"]

            # Generate new embedding
            embedding = await self.pinecone_client.embed_text(text, correlation_id)

            # Cache the embedding if Redis is available
            if redis_client:
                try:
                    await redis_client.set_json(
                        cache_key,
                        {
                            "embedding": embedding,
                            "text_hash": hashlib.md5(text.encode()).hexdigest(),
                        },
                        expiration=self.embedding_cache_ttl,
                        correlation_id=correlation_id,
                    )
                except Exception as cache_error:
                    logger.warning(f"Failed to cache embedding: {str(cache_error)}")

            return embedding

        except Exception as e:
            logger.error(
                f"Embedding generation failed: {str(e)}",
                extra={"correlation_id": correlation_id},
            )
            # Fallback to direct embedding generation
            return await self.pinecone_client.embed_text(text, correlation_id)

    async def _cache_results(
        self,
        query: str,
        top_k: int,
        use_hybrid: bool,
        documents: List[Dict[str, Any]],
        correlation_id: str,
    ) -> None:
        """Cache retrieval results."""
        try:
            redis_client = await self.get_redis_client()
            if not redis_client:
                return

            cache_key = self._generate_cache_key(query, top_k, use_hybrid)
            cache_data = {"documents": documents, "timestamp": time.time()}

            # Use fast cache for frequently accessed queries
            ttl = (
                self.fast_cache_ttl
                if len(self.retrieval_times) > 10
                else self.cache_ttl
            )

            await redis_client.set_json(
                cache_key,
                cache_data,
                expiration=ttl,
                correlation_id=correlation_id,
            )

        except Exception as e:
            logger.warning(
                f"Failed to cache results: {str(e)}",
                extra={"correlation_id": correlation_id},
            )

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get RAG service performance metrics."""
        if not self.retrieval_times:
            return {
                "avg_retrieval_time_ms": 0,
                "cache_hit_rate": 0,
                "total_retrievals": 0,
            }

        avg_time = sum(self.retrieval_times[-100:]) / len(
            self.retrieval_times[-100:]
        )  # Last 100 retrievals
        total_requests = self.cache_hit_count + self.cache_miss_count
        hit_rate = self.cache_hit_count / total_requests if total_requests > 0 else 0

        return {
            "avg_retrieval_time_ms": round(avg_time * 1000, 2),
            "cache_hit_rate": round(hit_rate, 3),
            "total_retrievals": len(self.retrieval_times),
            "cache_hits": self.cache_hit_count,
            "cache_misses": self.cache_miss_count,
            "p95_retrieval_time_ms": (
                round(sorted(self.retrieval_times[-100:])[-5] * 1000, 2)
                if len(self.retrieval_times) >= 5
                else 0
            ),
        }

    async def rerank_documents(
        self, query: str, documents: List[Dict[str, Any]], correlation_id: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Rerank documents for improved relevance.

        Args:
            query: Original user query
            documents: Retrieved documents to rerank
            correlation_id: Request correlation ID

        Returns:
            Reranked documents with updated scores
        """
        logger.info(
            f"Reranking documents",
            extra={"correlation_id": correlation_id, "document_count": len(documents)},
        )

        try:
            # Simple reranking based on query-document text similarity
            # TODO: Implement cross-encoder model for better reranking

            reranked_documents = []
            query_lower = query.lower()
            query_words = set(query_lower.split())

            for doc in documents:
                content = doc.get("content", "").lower()
                content_words = set(content.split())

                # Calculate word overlap score
                word_overlap = len(query_words.intersection(content_words))
                overlap_score = word_overlap / len(query_words) if query_words else 0

                # Combine with original similarity score
                base_score = doc.get("enhanced_score", doc.get("score", 0))
                rerank_score = (base_score * 0.7) + (overlap_score * 0.3)

                reranked_doc = {
                    **doc,
                    "rerank_score": rerank_score,
                    "word_overlap": word_overlap,
                    "overlap_ratio": overlap_score,
                }

                reranked_documents.append(reranked_doc)

            # Sort by rerank score
            reranked_documents.sort(key=lambda x: x["rerank_score"], reverse=True)

            logger.info(
                f"Document reranking completed",
                extra={
                    "correlation_id": correlation_id,
                    "avg_rerank_score": (
                        sum(doc["rerank_score"] for doc in reranked_documents)
                        / len(reranked_documents)
                        if reranked_documents
                        else 0
                    ),
                },
            )

            return reranked_documents

        except Exception as e:
            logger.error(
                f"Document reranking failed: {str(e)}",
                extra={"correlation_id": correlation_id},
            )
            # Return original documents on failure
            return documents

    async def _initialize_hybrid_search_index(self, correlation_id: str = "") -> None:
        """
        Initialize hybrid search index with existing documents.

        Args:
            correlation_id: Request correlation ID
        """
        try:
            # Get sample documents to build BM25 index
            # In production, you'd fetch all documents or use a pre-built index
            sample_query_embedding = await self.pinecone_client.embed_text(
                "fintech payment account security", correlation_id
            )

            all_documents = await self.pinecone_client.search_documents(
                query_embedding=sample_query_embedding,
                top_k=100,  # Get more documents for index building
                correlation_id=correlation_id,
            )

            if all_documents:
                self.hybrid_search.build_index(all_documents)
                self._index_initialized = True
                logger.info(
                    f"Hybrid search index initialized with {len(all_documents)} documents",
                    extra={"correlation_id": correlation_id},
                )
            else:
                logger.warning(
                    f"No documents found for hybrid search index initialization",
                    extra={"correlation_id": correlation_id},
                )

        except Exception as e:
            logger.error(
                f"Failed to initialize hybrid search index: {str(e)}",
                extra={"correlation_id": correlation_id},
            )
            # Continue without hybrid search
            self._index_initialized = False

    def _get_relevance_tier(self, score: float) -> str:
        """
        Categorize relevance score into tiers.

        Args:
            score: Relevance score

        Returns:
            Relevance tier string
        """
        if score >= 0.8:
            return "high"
        elif score >= 0.6:
            return "medium"
        elif score >= 0.4:
            return "low"
        else:
            return "very_low"

    async def build_context_prompt(
        self,
        documents: List[Dict[str, Any]],
        max_length: int = 2000,
        correlation_id: str = "",
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build context prompt from retrieved documents with token awareness.

        Args:
            documents: Retrieved and ranked documents
            max_length: Maximum context length in characters (fallback)
            correlation_id: Request correlation ID

        Returns:
            Tuple of (formatted context string, context metadata)
        """
        if not documents:
            return "", {"token_count": 0, "documents_included": 0}

        # Use hybrid search service for token-aware context building
        context, metadata = self.hybrid_search.build_context_with_tokens(
            documents, correlation_id
        )

        # Fallback to character-based limiting if context is still too long
        if not context and max_length > 0:
            context_parts = []
            current_length = 0
            documents_included = 0

            for i, doc in enumerate(documents):
                content = doc.get("content", "").strip()
                if not content:
                    continue

                # Format document section with attribution
                doc_section = f"[Document {i+1}]"

                # Add source attribution if available
                source_attr = doc.get("source_attribution", {})
                if source_attr.get("category"):
                    doc_section += f" ({source_attr['category']})"
                if source_attr.get("source") and source_attr["source"] != "unknown":
                    doc_section += f" - Source: {source_attr['source']}"

                doc_section += f"\n{content}\n"

                # Check if adding this document would exceed limit
                if current_length + len(doc_section) > max_length:
                    break

                context_parts.append(doc_section)
                current_length += len(doc_section)
                documents_included += 1

            if context_parts:
                context = f"Relevant information from knowledge base:\n\n" + "\n".join(
                    context_parts
                )
                metadata = {
                    "token_count": current_length,  # Approximate
                    "documents_included": documents_included,
                    "documents_available": len(documents),
                    "truncated": documents_included < len(documents),
                    "method": "character_based_fallback",
                }
            else:
                context = ""
                metadata = {
                    "token_count": 0,
                    "documents_included": 0,
                    "method": "fallback_empty",
                }

        logger.info(
            f"Context prompt built",
            extra={"correlation_id": correlation_id, **metadata},
        )

        return context, metadata
