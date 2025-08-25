"""
RAG (Retrieval-Augmented Generation) service for document retrieval.

Implements complete RAG pipeline with Pinecone vector search,
embedding generation, and context optimization for AI responses.
"""

import logging
from typing import Any, Dict, List, Tuple

from app.integrations.pinecone_client import PineconeClient
from app.integrations.redis_client import get_redis_client
from app.services.hybrid_search_service import HybridSearchService

logger = logging.getLogger(__name__)


class RAGService:
    """Service for RAG pipeline operations with Pinecone and context management."""

    def __init__(self) -> None:
        """Initialize RAG service with Pinecone client and hybrid search."""
        self.pinecone_client = PineconeClient()
        self.hybrid_search = HybridSearchService(
            vector_weight=0.7,  # 70% vector similarity
            keyword_weight=0.3,  # 30% keyword matching
            diversity_threshold=0.85,
            max_context_tokens=8000,
        )
        self._index_initialized = False
        logger.info("RAG service initialized with Pinecone client and hybrid search")

    async def retrieve_context(
        self,
        query: str,
        top_k: int = 5,
        correlation_id: str = "",
        use_hybrid_search: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context documents from Pinecone.

        Args:
            query: User query for semantic search
            top_k: Number of documents to retrieve
            correlation_id: Request correlation ID
            use_hybrid_search: Whether to use hybrid search (default: True)

        Returns:
            List of relevant document chunks with metadata
        """
        logger.info(
            f"Retrieving context for query",
            extra={
                "correlation_id": correlation_id,
                "query_length": len(query),
                "top_k": top_k,
            },
        )

        try:
            # Check cache first
            redis_client = await get_redis_client()
            cache_key = f"rag_context:{hash(query)}:{top_k}:{'hybrid' if use_hybrid_search else 'vector'}"
            cached_results = await redis_client.get_json(cache_key, correlation_id)

            if cached_results and "documents" in cached_results:
                logger.info(
                    f"Retrieved context from cache",
                    extra={"correlation_id": correlation_id},
                )
                return cached_results["documents"]

            # Generate query embedding
            query_embedding = await self.pinecone_client.embed_text(
                query, correlation_id
            )

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

            # Cache results for 5 minutes
            cache_data: Dict[str, Any] = {"documents": enhanced_documents}
            await redis_client.set_json(
                cache_key,
                cache_data,
                expiration=300,
                correlation_id=correlation_id,
            )

            # Limit to requested top_k
            final_documents = enhanced_documents[:top_k]

            logger.info(
                f"Context retrieval completed",
                extra={
                    "correlation_id": correlation_id,
                    "search_type": "hybrid" if use_hybrid_search else "vector_only",
                    "documents_found": len(final_documents),
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
