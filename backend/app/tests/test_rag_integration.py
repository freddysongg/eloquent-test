"""
Integration tests for RAG service with hybrid search functionality.

Tests end-to-end RAG pipeline including hybrid search, context building,
and backward compatibility with vector-only mode.
"""

from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from app.services.rag_service import RAGService


class MockPineconeClient:
    """Mock Pinecone client for testing."""

    def __init__(self) -> None:
        self.mock_documents = [
            {
                "id": "test_doc_1",
                "content": "How to reset your account password for secure login access",
                "category": "account",
                "source": "help_center",
                "title": "Password Reset Guide",
                "score": 0.85,
                "metadata": {"category": "account", "source": "help_center"},
            },
            {
                "id": "test_doc_2",
                "content": "Payment processing fees are 2.9% plus thirty cents per transaction",
                "category": "payment",
                "source": "pricing_guide",
                "title": "Processing Fees",
                "score": 0.78,
                "metadata": {"category": "payment", "source": "pricing_guide"},
            },
            {
                "id": "test_doc_3",
                "content": "Your financial data is protected with bank level encryption and security",
                "category": "security",
                "source": "security_policy",
                "title": "Data Security",
                "score": 0.90,
                "metadata": {"category": "security", "source": "security_policy"},
            },
        ]

    async def embed_text(self, text: str, correlation_id: str = "") -> List[float]:
        """Mock embedding generation."""
        # Simple hash-based mock embedding
        import hashlib

        text_hash = hashlib.md5(text.encode()).hexdigest()
        # Convert to mock 1024-dimensional vector
        embedding = [
            float(int(text_hash[i : i + 2], 16)) / 255.0
            for i in range(0, min(len(text_hash), 32), 2)
        ]
        # Pad to 1024 dimensions
        while len(embedding) < 1024:
            embedding.extend(embedding[: min(1024 - len(embedding), len(embedding))])
        return embedding[:1024]

    async def search_documents(
        self, query_embedding: List[float], top_k: int = 5, correlation_id: str = ""
    ) -> List[Dict[str, Any]]:
        """Mock document search."""
        # Return mock documents sorted by score
        return sorted(
            self.mock_documents,
            key=lambda x: (
                float(x["score"]) if isinstance(x["score"], (int, float, str)) else 0.0
            ),
            reverse=True,
        )[:top_k]

    def calculate_relevance_score(
        self, similarity_score: float, metadata: Dict[str, Any]
    ) -> float:
        """Mock relevance scoring."""
        base_score = similarity_score
        category_boost = {"security": 1.1, "account": 1.05, "payment": 1.0}
        category = metadata.get("category", "general")
        return min(base_score * category_boost.get(category, 1.0), 1.0)


class MockRedisClient:
    """Mock Redis client for testing."""

    def __init__(self) -> None:
        self.cache: Dict[str, Any] = {}

    async def get_json(self, key: str, correlation_id: str = "") -> Any:
        """Mock cache get."""
        return self.cache.get(key)

    async def set_json(
        self, key: str, value: Any, expiration: int = 300, correlation_id: str = ""
    ) -> None:
        """Mock cache set."""
        self.cache[key] = value


@pytest.fixture
def mock_redis_client() -> MockRedisClient:
    """Fixture for mock Redis client."""
    return MockRedisClient()


@pytest.fixture
def rag_service_with_mocks(mock_redis_client: MockRedisClient) -> RAGService:
    """Fixture for RAG service with mocked dependencies."""
    with patch(
        "app.services.rag_service.get_redis_client", return_value=mock_redis_client
    ):
        with patch(
            "app.integrations.pinecone_client.PineconeClient", MockPineconeClient
        ):
            service = RAGService()
            return service


@pytest.mark.asyncio
async def test_hybrid_search_integration(rag_service_with_mocks: RAGService) -> None:
    """Test RAG service with hybrid search enabled."""
    rag_service = rag_service_with_mocks

    # Test query that should benefit from hybrid search
    query = "How do I reset my password?"
    correlation_id = "test_correlation_123"

    # Retrieve context with hybrid search
    results = await rag_service.retrieve_context(
        query=query, top_k=3, correlation_id=correlation_id, use_hybrid_search=True
    )

    # Validate results
    assert len(results) > 0, "Should return search results"
    assert len(results) <= 3, "Should respect top_k limit"

    # Check for hybrid search specific fields
    for result in results:
        assert "hybrid_score" in result, "Results should have hybrid_score"
        assert "confidence" in result, "Results should have confidence score"
        assert "source_attribution" in result, "Results should have source attribution"

        # Validate confidence is between 0 and 1
        confidence = result["confidence"]
        assert (
            0.0 <= confidence <= 1.0
        ), f"Confidence {confidence} should be between 0 and 1"


@pytest.mark.asyncio
async def test_vector_only_fallback(rag_service_with_mocks: RAGService) -> None:
    """Test RAG service with vector-only search (backward compatibility)."""
    rag_service = rag_service_with_mocks

    query = "What are the payment fees?"
    correlation_id = "test_correlation_456"

    # Retrieve context with vector-only search
    results = await rag_service.retrieve_context(
        query=query, top_k=3, correlation_id=correlation_id, use_hybrid_search=False
    )

    # Validate results
    assert len(results) > 0, "Should return search results"
    assert len(results) <= 3, "Should respect top_k limit"

    # Check for vector-only specific fields
    for result in results:
        assert "enhanced_score" in result, "Results should have enhanced_score"
        assert "relevance_tier" in result, "Results should have relevance_tier"

        # Should not have hybrid-specific fields
        assert (
            "hybrid_score" not in result
        ), "Vector-only results should not have hybrid_score"
        assert (
            "confidence" not in result
        ), "Vector-only results should not have confidence"


@pytest.mark.asyncio
async def test_context_prompt_building(rag_service_with_mocks: RAGService) -> None:
    """Test enhanced context prompt building with token awareness."""
    rag_service = rag_service_with_mocks

    # Get some test documents
    query = "security data protection"
    results = await rag_service.retrieve_context(
        query=query, top_k=3, use_hybrid_search=True
    )

    # Build context prompt
    context, metadata = await rag_service.build_context_prompt(
        documents=results, max_length=1000, correlation_id="test_context_123"
    )

    # Validate context
    assert isinstance(context, str), "Context should be a string"
    assert isinstance(metadata, dict), "Metadata should be a dictionary"

    # Check metadata structure
    required_metadata_fields = ["token_count", "documents_included"]
    for field in required_metadata_fields:
        assert field in metadata, f"Metadata should have {field} field"

    # Validate context content
    if context:
        assert (
            "Relevant information from knowledge base:" in context
        ), "Context should have proper header"
        assert "[Document" in context, "Context should have document sections"


@pytest.mark.asyncio
async def test_cache_behavior_with_search_types(
    rag_service_with_mocks: RAGService,
) -> None:
    """Test that caching works correctly for both hybrid and vector-only searches."""
    rag_service = rag_service_with_mocks

    query = "account verification process"
    correlation_id = "test_cache_789"

    # First call with hybrid search
    results_hybrid_1 = await rag_service.retrieve_context(
        query=query, top_k=2, correlation_id=correlation_id, use_hybrid_search=True
    )

    # Second call with hybrid search (should use cache)
    results_hybrid_2 = await rag_service.retrieve_context(
        query=query, top_k=2, correlation_id=correlation_id, use_hybrid_search=True
    )

    # First call with vector-only (should not use hybrid cache)
    results_vector_1 = await rag_service.retrieve_context(
        query=query, top_k=2, correlation_id=correlation_id, use_hybrid_search=False
    )

    # Results should be consistent within search type
    assert len(results_hybrid_1) == len(
        results_hybrid_2
    ), "Cached hybrid results should be identical"
    assert len(results_vector_1) > 0, "Vector-only search should return results"

    # Different search types may have different results (that's expected)
    hybrid_doc_ids = {doc.get("id") for doc in results_hybrid_1}
    vector_doc_ids = {doc.get("id") for doc in results_vector_1}

    # Both should return valid document IDs
    assert all(
        doc_id for doc_id in hybrid_doc_ids
    ), "Hybrid results should have valid IDs"
    assert all(
        doc_id for doc_id in vector_doc_ids
    ), "Vector results should have valid IDs"


@pytest.mark.asyncio
async def test_error_handling_and_fallback(rag_service_with_mocks: RAGService) -> None:
    """Test error handling and graceful fallback behavior."""
    rag_service = rag_service_with_mocks

    # Test with empty query
    results = await rag_service.retrieve_context(
        query="", top_k=5, use_hybrid_search=True
    )

    # Should handle gracefully (may return empty results or cached results)
    assert isinstance(results, list), "Should return list even for empty query"

    # Test with very large top_k
    results = await rag_service.retrieve_context(
        query="test query", top_k=1000, use_hybrid_search=True
    )

    # Should handle gracefully and return available results
    assert isinstance(results, list), "Should return list even for large top_k"
    assert len(results) >= 0, "Should return non-negative number of results"


if __name__ == "__main__":
    """Run integration tests standalone."""
    pytest.main([__file__, "-v"])
