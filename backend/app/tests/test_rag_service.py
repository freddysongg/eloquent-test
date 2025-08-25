"""
Comprehensive unit tests for RAG Service.

Tests all RAG service methods including context retrieval, document reranking,
context building, caching behavior, error handling, and performance requirements.
"""

import asyncio
import time
from typing import Any, Dict, List
from unittest.mock import Mock, patch

import pytest
from tests.conftest import (
    TEST_CORRELATION_ID,
    assert_performance_benchmark,
    assert_valid_search_results,
)

from app.core.exceptions import ExternalServiceException
from app.services.rag_service import RAGService


@pytest.mark.unit
class TestRAGServiceInitialization:
    """Test RAG service initialization."""

    def test_rag_service_initialization(
        self, rag_service_with_mocks: RAGService
    ) -> None:
        """Test RAG service initializes correctly."""
        service = rag_service_with_mocks

        assert service is not None
        assert service.pinecone_client is not None
        assert service.hybrid_search is not None
        assert service._index_initialized is False
        assert service.hybrid_search.vector_weight == 0.7
        assert service.hybrid_search.keyword_weight == 0.3
        assert service.hybrid_search.diversity_threshold == 0.85


@pytest.mark.unit
class TestRAGServiceContextRetrieval:
    """Test context retrieval functionality."""

    @pytest.mark.asyncio
    async def test_retrieve_context_hybrid_search_success(
        self,
        rag_service_with_mocks: RAGService,
        sample_documents: List[Dict[str, Any]],
        performance_benchmarks: Dict[str, float],
    ) -> None:
        """Test successful context retrieval with hybrid search."""
        service = rag_service_with_mocks
        query = "How do I reset my password?"
        top_k = 3

        start_time = time.time()
        results = await service.retrieve_context(
            query=query,
            top_k=top_k,
            correlation_id=TEST_CORRELATION_ID,
            use_hybrid_search=True,
        )

        # Performance validation
        assert_performance_benchmark(
            start_time, performance_benchmarks["rag_query_ms"], "Context retrieval"
        )

        # Result validation
        assert_valid_search_results(results, top_k)
        assert len(results) <= top_k

        # Verify hybrid search fields are present
        for result in results:
            if "hybrid_score" in result:  # Hybrid search was used
                assert "confidence" in result
                assert "source_attribution" in result
                assert 0.0 <= result["confidence"] <= 1.0

        # Verify service calls
        service.pinecone_client.embed_text.assert_called_once_with(  # type: ignore[attr-defined]
            query, TEST_CORRELATION_ID
        )
        service.pinecone_client.search_documents.assert_called_once()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_retrieve_context_vector_only_fallback(
        self, rag_service_with_mocks: RAGService, sample_documents: List[Dict[str, Any]]
    ) -> None:
        """Test context retrieval with vector-only search fallback."""
        service = rag_service_with_mocks
        query = "What are payment fees?"
        top_k = 2

        results = await service.retrieve_context(
            query=query,
            top_k=top_k,
            correlation_id=TEST_CORRELATION_ID,
            use_hybrid_search=False,
        )

        # Result validation
        assert_valid_search_results(results, top_k)

        # Verify vector-only fields are present
        for result in results:
            assert "enhanced_score" in result
            assert "relevance_tier" in result
            # Should not have hybrid-specific fields
            assert "hybrid_score" not in result
            assert "confidence" not in result

    @pytest.mark.asyncio
    async def test_retrieve_context_empty_query(
        self, rag_service_with_mocks: RAGService
    ) -> None:
        """Test context retrieval with empty query."""
        service = rag_service_with_mocks

        results = await service.retrieve_context(
            query="", top_k=5, correlation_id=TEST_CORRELATION_ID
        )

        # Should handle gracefully
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_retrieve_context_large_top_k(
        self, rag_service_with_mocks: RAGService
    ) -> None:
        """Test context retrieval with very large top_k."""
        service = rag_service_with_mocks

        results = await service.retrieve_context(
            query="test query",
            top_k=1000,  # Much larger than available documents
            correlation_id=TEST_CORRELATION_ID,
        )

        # Should handle gracefully and return available results
        assert isinstance(results, list)
        assert len(results) >= 0

    @pytest.mark.asyncio
    async def test_retrieve_context_caching_behavior(
        self, rag_service_with_mocks: RAGService, mock_redis_client: Any
    ) -> None:
        """Test that context retrieval uses caching correctly."""
        service = rag_service_with_mocks
        query = "cached query test"
        top_k = 3

        # First call - should cache results
        results1 = await service.retrieve_context(
            query=query,
            top_k=top_k,
            correlation_id=TEST_CORRELATION_ID,
            use_hybrid_search=True,
        )

        # Verify cache was written
        cache_key = f"rag_context:{hash(query)}:{top_k}:hybrid"
        cached_data = await mock_redis_client.get_json(cache_key)
        assert cached_data is not None

        # Second call - should use cache
        results2 = await service.retrieve_context(
            query=query,
            top_k=top_k,
            correlation_id=TEST_CORRELATION_ID,
            use_hybrid_search=True,
        )

        # Results should be identical
        assert len(results1) == len(results2)
        if results1 and results2:
            assert results1[0]["id"] == results2[0]["id"]

    @pytest.mark.asyncio
    async def test_retrieve_context_different_search_types_cached_separately(
        self, rag_service_with_mocks: RAGService, mock_redis_client: Any
    ) -> None:
        """Test that hybrid and vector-only searches are cached separately."""
        service = rag_service_with_mocks
        query = "search type test"
        top_k = 3

        # Call with hybrid search
        results_hybrid = await service.retrieve_context(
            query=query, top_k=top_k, use_hybrid_search=True
        )

        # Call with vector-only
        results_vector = await service.retrieve_context(
            query=query, top_k=top_k, use_hybrid_search=False
        )

        # Should have separate cache entries
        hybrid_cache_key = f"rag_context:{hash(query)}:{top_k}:hybrid"
        vector_cache_key = f"rag_context:{hash(query)}:{top_k}:vector_only"

        hybrid_cached = await mock_redis_client.get_json(hybrid_cache_key)
        vector_cached = await mock_redis_client.get_json(vector_cache_key)

        assert hybrid_cached is not None
        assert vector_cached is not None
        # They may be different due to different search strategies
        assert isinstance(results_hybrid, list)
        assert isinstance(results_vector, list)

    @pytest.mark.asyncio
    async def test_retrieve_context_pinecone_failure_returns_empty(
        self, rag_service_with_mocks: RAGService
    ) -> None:
        """Test that Pinecone failures return empty results gracefully."""
        service = rag_service_with_mocks

        # Mock Pinecone client to raise exception
        service.pinecone_client.embed_text.side_effect = Exception("Pinecone error")  # type: ignore[attr-defined]

        results = await service.retrieve_context(
            query="test query", top_k=5, correlation_id=TEST_CORRELATION_ID
        )

        # Should return empty list instead of raising
        assert results == []


@pytest.mark.unit
class TestRAGServiceDocumentReranking:
    """Test document reranking functionality."""

    @pytest.mark.asyncio
    async def test_rerank_documents_success(
        self, rag_service_with_mocks: RAGService, sample_documents: List[Dict[str, Any]]
    ) -> None:
        """Test successful document reranking."""
        service = rag_service_with_mocks
        query = "password reset account"

        results = await service.rerank_documents(
            query=query,
            documents=sample_documents[:3],
            correlation_id=TEST_CORRELATION_ID,
        )

        # Verify reranking fields are added
        assert len(results) == 3
        for result in results:
            assert "rerank_score" in result
            assert "word_overlap" in result
            assert "overlap_ratio" in result
            assert isinstance(result["rerank_score"], (int, float))
            assert isinstance(result["word_overlap"], int)
            assert 0.0 <= result["overlap_ratio"] <= 1.0

        # Results should be sorted by rerank_score
        scores = [result["rerank_score"] for result in results]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_rerank_documents_empty_list(
        self, rag_service_with_mocks: RAGService
    ) -> None:
        """Test reranking with empty document list."""
        service = rag_service_with_mocks

        results = await service.rerank_documents(
            query="test query", documents=[], correlation_id=TEST_CORRELATION_ID
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_rerank_documents_failure_returns_original(
        self, rag_service_with_mocks: RAGService, sample_documents: List[Dict[str, Any]]
    ) -> None:
        """Test that reranking failures return original documents."""
        service = rag_service_with_mocks

        # Create a scenario that might cause reranking to fail
        documents_with_none_content = [
            {**doc, "content": None} for doc in sample_documents[:2]
        ]

        results = await service.rerank_documents(
            query="test query",
            documents=documents_with_none_content,
            correlation_id=TEST_CORRELATION_ID,
        )

        # Should return original documents on failure
        assert len(results) == 2
        for result in results:
            assert result["content"] is None  # Original data preserved

    @pytest.mark.asyncio
    async def test_rerank_documents_word_overlap_calculation(
        self, rag_service_with_mocks: RAGService
    ) -> None:
        """Test word overlap calculation in reranking."""
        service = rag_service_with_mocks
        query = "password reset"

        # Document with exact query terms
        test_documents = [
            {
                "id": "exact_match",
                "content": "To reset your password, follow these steps",
                "score": 0.5,
            },
            {
                "id": "no_match",
                "content": "Account verification requires documentation",
                "score": 0.9,  # Higher original score
            },
        ]

        results = await service.rerank_documents(
            query=query, documents=test_documents, correlation_id=TEST_CORRELATION_ID
        )

        # Exact match should have higher word overlap
        exact_match = next(r for r in results if r["id"] == "exact_match")
        no_match = next(r for r in results if r["id"] == "no_match")

        assert exact_match["word_overlap"] > no_match["word_overlap"]
        assert exact_match["overlap_ratio"] > no_match["overlap_ratio"]

        # Rerank score should consider both original score and overlap
        assert "rerank_score" in exact_match
        assert "rerank_score" in no_match


@pytest.mark.unit
class TestRAGServiceContextBuilding:
    """Test context prompt building functionality."""

    @pytest.mark.asyncio
    async def test_build_context_prompt_success(
        self,
        rag_service_with_mocks: RAGService,
        sample_documents: List[Dict[str, Any]],
        performance_benchmarks: Dict[str, float],
    ) -> None:
        """Test successful context prompt building."""
        service = rag_service_with_mocks
        documents = sample_documents[:3]

        start_time = time.time()
        context, metadata = await service.build_context_prompt(
            documents=documents, max_length=2000, correlation_id=TEST_CORRELATION_ID
        )

        # Performance validation
        assert_performance_benchmark(
            start_time,
            performance_benchmarks["context_building_ms"],
            "Context building",
        )

        # Context validation
        assert isinstance(context, str)
        assert isinstance(metadata, dict)
        assert len(context) > 0

        # Metadata validation
        required_fields = ["token_count", "documents_included"]
        for field in required_fields:
            assert field in metadata

        assert metadata["documents_included"] <= len(documents)
        assert metadata["token_count"] >= 0

        # Content validation
        assert "Relevant information from knowledge base:" in context
        assert "[Document" in context

    @pytest.mark.asyncio
    async def test_build_context_prompt_empty_documents(
        self, rag_service_with_mocks: RAGService
    ) -> None:
        """Test context building with empty document list."""
        service = rag_service_with_mocks

        context, metadata = await service.build_context_prompt(
            documents=[], max_length=1000, correlation_id=TEST_CORRELATION_ID
        )

        assert context == ""
        assert metadata["token_count"] == 0
        assert metadata["documents_included"] == 0

    @pytest.mark.asyncio
    async def test_build_context_prompt_with_attribution(
        self, rag_service_with_mocks: RAGService
    ) -> None:
        """Test context building includes proper attribution."""
        service = rag_service_with_mocks

        # Documents with source attribution
        documents_with_attribution = [
            {
                "id": "test_doc_1",
                "content": "Test content for attribution",
                "source_attribution": {
                    "category": "security",
                    "source": "security_policy",
                    "title": "Security Guidelines",
                },
            }
        ]

        context, metadata = await service.build_context_prompt(
            documents=documents_with_attribution,
            max_length=1000,
            correlation_id=TEST_CORRELATION_ID,
        )

        # Check attribution appears in context
        assert "security" in context
        assert "security_policy" in context
        assert "Test content for attribution" in context

    @pytest.mark.asyncio
    async def test_build_context_prompt_length_limiting(
        self, rag_service_with_mocks: RAGService
    ) -> None:
        """Test context building respects length limits."""
        service = rag_service_with_mocks

        # Create documents with long content
        long_documents = [
            {
                "id": f"long_doc_{i}",
                "content": "This is a very long document. " * 100,  # 500+ characters
                "score": 0.8,
            }
            for i in range(5)
        ]

        max_length = 800  # Should only fit 1-2 documents
        context, metadata = await service.build_context_prompt(
            documents=long_documents,
            max_length=max_length,
            correlation_id=TEST_CORRELATION_ID,
        )

        # Should respect length limit
        assert len(context) <= max_length * 1.1  # Small tolerance for formatting
        assert metadata["documents_included"] < len(long_documents)
        assert metadata["truncated"] is True

    @pytest.mark.asyncio
    async def test_build_context_prompt_hybrid_search_token_aware(
        self, rag_service_with_mocks: RAGService, sample_documents: List[Dict[str, Any]]
    ) -> None:
        """Test that context building uses hybrid search token-aware method."""
        service = rag_service_with_mocks

        # Mock the hybrid search service to return token-aware context
        service.hybrid_search.build_context_with_tokens = Mock(  # type: ignore[method-assign]
            return_value=(
                "Token-aware context from hybrid search",
                {"token_count": 150, "documents_included": 2},
            )
        )

        context, metadata = await service.build_context_prompt(
            documents=sample_documents[:3],
            max_length=2000,
            correlation_id=TEST_CORRELATION_ID,
        )

        # Should use hybrid search method
        service.hybrid_search.build_context_with_tokens.assert_called_once()
        assert context == "Token-aware context from hybrid search"
        assert metadata["token_count"] == 150
        assert metadata["documents_included"] == 2


@pytest.mark.unit
class TestRAGServicePrivateMethods:
    """Test private methods of RAG service."""

    @pytest.mark.asyncio
    async def test_initialize_hybrid_search_index(
        self, rag_service_with_mocks: RAGService, sample_documents: List[Dict[str, Any]]
    ) -> None:
        """Test hybrid search index initialization."""
        service = rag_service_with_mocks

        # Mock the search to return documents for index building
        service.pinecone_client.search_documents.return_value = sample_documents  # type: ignore[attr-defined]

        # Initialize index
        await service._initialize_hybrid_search_index(TEST_CORRELATION_ID)

        # Should set index as initialized
        assert service._index_initialized is True

        # Should have called embed_text and search_documents
        service.pinecone_client.embed_text.assert_called_once()  # type: ignore[attr-defined]
        service.pinecone_client.search_documents.assert_called_once()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_initialize_hybrid_search_index_failure(
        self, rag_service_with_mocks: RAGService
    ) -> None:
        """Test hybrid search index initialization failure handling."""
        service = rag_service_with_mocks

        # Mock to raise exception
        service.pinecone_client.embed_text.side_effect = Exception("Index init failed")  # type: ignore[attr-defined]

        # Should not raise exception
        await service._initialize_hybrid_search_index(TEST_CORRELATION_ID)

        # Should remain uninitialized
        assert service._index_initialized is False

    def test_get_relevance_tier(self, rag_service_with_mocks: RAGService) -> None:
        """Test relevance tier calculation."""
        service = rag_service_with_mocks

        # Test different score ranges
        assert service._get_relevance_tier(0.95) == "high"
        assert service._get_relevance_tier(0.8) == "high"
        assert service._get_relevance_tier(0.75) == "medium"
        assert service._get_relevance_tier(0.6) == "medium"
        assert service._get_relevance_tier(0.5) == "low"
        assert service._get_relevance_tier(0.4) == "low"
        assert service._get_relevance_tier(0.35) == "very_low"
        assert service._get_relevance_tier(0.1) == "very_low"


@pytest.mark.unit
class TestRAGServiceErrorHandling:
    """Test error handling in RAG service."""

    @pytest.mark.asyncio
    async def test_retrieve_context_embedding_failure(
        self, rag_service_with_mocks: RAGService
    ) -> None:
        """Test context retrieval when embedding generation fails."""
        service = rag_service_with_mocks

        # Mock embedding to fail
        service.pinecone_client.embed_text.side_effect = ExternalServiceException(  # type: ignore[attr-defined]
            "embedding_api", "Embedding generation failed"
        )

        results = await service.retrieve_context(
            query="test query", top_k=5, correlation_id=TEST_CORRELATION_ID
        )

        # Should return empty list gracefully
        assert results == []

    @pytest.mark.asyncio
    async def test_retrieve_context_search_failure(
        self, rag_service_with_mocks: RAGService, test_query_embedding: List[float]
    ) -> None:
        """Test context retrieval when Pinecone search fails."""
        service = rag_service_with_mocks

        # Mock embedding to succeed but search to fail
        service.pinecone_client.embed_text.return_value = test_query_embedding  # type: ignore[attr-defined]
        service.pinecone_client.search_documents.side_effect = ExternalServiceException(  # type: ignore[attr-defined]
            "pinecone", "Search failed"
        )

        results = await service.retrieve_context(
            query="test query", top_k=5, correlation_id=TEST_CORRELATION_ID
        )

        # Should return empty list gracefully
        assert results == []

    @pytest.mark.asyncio
    async def test_retrieve_context_cache_failure_continues(
        self, rag_service_with_mocks: RAGService, mock_get_redis_client: Any
    ) -> None:
        """Test that cache failures don't prevent context retrieval."""
        service = rag_service_with_mocks

        # Mock Redis client to fail
        async def failing_redis() -> None:
            raise Exception("Redis connection failed")

        with patch(
            "app.services.rag_service.get_redis_client", side_effect=failing_redis
        ):
            results = await service.retrieve_context(
                query="test query", top_k=3, correlation_id=TEST_CORRELATION_ID
            )

        # Should still return results from Pinecone
        assert isinstance(results, list)
        # Should have called Pinecone despite cache failure
        service.pinecone_client.embed_text.assert_called_once()  # type: ignore[attr-defined]


@pytest.mark.unit
class TestRAGServicePerformance:
    """Test performance characteristics of RAG service."""

    @pytest.mark.asyncio
    async def test_retrieve_context_performance_benchmark(
        self,
        rag_service_with_mocks: RAGService,
        performance_benchmarks: Dict[str, float],
    ) -> None:
        """Test that context retrieval meets performance benchmarks."""
        service = rag_service_with_mocks

        start_time = time.time()
        results = await service.retrieve_context(
            query="performance test query", top_k=5, correlation_id=TEST_CORRELATION_ID
        )

        # Should meet performance benchmark
        assert_performance_benchmark(
            start_time, performance_benchmarks["rag_query_ms"], "RAG query performance"
        )

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_build_context_prompt_performance_benchmark(
        self,
        rag_service_with_mocks: RAGService,
        sample_documents: List[Dict[str, Any]],
        performance_benchmarks: Dict[str, float],
    ) -> None:
        """Test that context building meets performance benchmarks."""
        service = rag_service_with_mocks

        start_time = time.time()
        context, metadata = await service.build_context_prompt(
            documents=sample_documents,
            max_length=2000,
            correlation_id=TEST_CORRELATION_ID,
        )

        # Should meet performance benchmark
        assert_performance_benchmark(
            start_time,
            performance_benchmarks["context_building_ms"],
            "Context building performance",
        )

        assert isinstance(context, str)
        assert isinstance(metadata, dict)

    @pytest.mark.asyncio
    async def test_concurrent_retrieve_context_calls(
        self, rag_service_with_mocks: RAGService
    ) -> None:
        """Test concurrent context retrieval calls."""
        service = rag_service_with_mocks

        # Create multiple concurrent calls
        queries = [f"query {i}" for i in range(5)]

        start_time = time.time()
        tasks = [
            service.retrieve_context(
                query=query, top_k=3, correlation_id=f"{TEST_CORRELATION_ID}_{i}"
            )
            for i, query in enumerate(queries)
        ]

        results_list = await asyncio.gather(*tasks)
        duration = time.time() - start_time

        # All calls should complete successfully
        assert len(results_list) == len(queries)
        for results in results_list:
            assert isinstance(results, list)

        # Concurrent execution should not take much longer than sequential
        assert duration < 2.0  # Reasonable time for 5 concurrent calls


@pytest.mark.unit
class TestRAGServiceIntegration:
    """Test integration between RAG service components."""

    @pytest.mark.asyncio
    async def test_full_rag_pipeline_flow(
        self,
        rag_service_with_mocks: RAGService,
        sample_documents: List[Dict[str, Any]],
        performance_benchmarks: Dict[str, float],
    ) -> None:
        """Test complete RAG pipeline from query to context."""
        service = rag_service_with_mocks
        query = "How do I secure my account?"

        start_time = time.time()

        # Step 1: Retrieve context
        documents = await service.retrieve_context(
            query=query,
            top_k=5,
            correlation_id=TEST_CORRELATION_ID,
            use_hybrid_search=True,
        )

        # Step 2: Rerank documents
        reranked_docs = await service.rerank_documents(
            query=query, documents=documents, correlation_id=TEST_CORRELATION_ID
        )

        # Step 3: Build context prompt
        context, metadata = await service.build_context_prompt(
            documents=reranked_docs, max_length=2000, correlation_id=TEST_CORRELATION_ID
        )

        # Performance validation
        assert_performance_benchmark(
            start_time,
            performance_benchmarks["rag_query_ms"] * 2,  # Allow 2x for full pipeline
            "Full RAG pipeline",
        )

        # Validate end-to-end results
        assert isinstance(documents, list)
        assert isinstance(reranked_docs, list)
        assert isinstance(context, str)
        assert isinstance(metadata, dict)

        # Context should contain relevant information
        if context:
            assert "Relevant information from knowledge base:" in context
            assert len(context) > 0
            assert metadata["documents_included"] > 0

    @pytest.mark.asyncio
    async def test_rag_service_with_real_hybrid_search(
        self,
        mock_pinecone_client: Any,
        mock_get_redis_client: Any,
        sample_documents: List[Dict[str, Any]],
    ) -> None:
        """Test RAG service with real hybrid search service (not mocked)."""
        # Create service with real hybrid search
        with (
            patch(
                "app.services.rag_service.PineconeClient",
                return_value=mock_pinecone_client,
            ),
            patch("app.services.rag_service.get_redis_client", mock_get_redis_client),
        ):
            service = RAGService()
            service.pinecone_client = mock_pinecone_client

            # Initialize hybrid search with test data
            service.hybrid_search.build_index(sample_documents)
            service._index_initialized = True

            query = "payment processing fees"
            results = await service.retrieve_context(
                query=query,
                top_k=3,
                correlation_id=TEST_CORRELATION_ID,
                use_hybrid_search=True,
            )

            # Should return hybrid search results
            assert isinstance(results, list)
            if results:
                # Check for hybrid search fields
                assert any("hybrid_score" in result for result in results)
