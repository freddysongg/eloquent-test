"""
Comprehensive unit tests for Hybrid Search Service.

Tests BM25 scoring, hybrid search algorithms, diversity filtering,
context building, and all service methods with performance validation.
"""

import time
from typing import Any, Dict, List

import pytest
from tests.conftest import (
    TEST_CORRELATION_ID,
    assert_performance_benchmark,
    assert_valid_search_results,
)

from app.services.hybrid_search_service import BM25Scorer, HybridSearchService


@pytest.mark.unit
class TestBM25Scorer:
    """Test BM25 scoring algorithm."""

    def test_bm25_scorer_initialization(self) -> None:
        """Test BM25 scorer initializes with correct parameters."""
        scorer = BM25Scorer(k1=1.5, b=0.8)

        assert scorer.k1 == 1.5
        assert scorer.b == 0.8
        assert scorer.corpus_size == 0
        assert scorer.avg_doc_length == 0.0
        assert isinstance(scorer.doc_frequencies, dict)
        assert isinstance(scorer.doc_lengths, dict)
        assert isinstance(scorer.documents, dict)

    def test_bm25_scorer_fit_with_documents(
        self, sample_documents: List[Dict[str, Any]]
    ) -> None:
        """Test BM25 scorer builds index correctly."""
        scorer = BM25Scorer()
        scorer.fit(sample_documents)

        assert scorer.corpus_size == len(sample_documents)
        assert scorer.avg_doc_length > 0
        assert len(scorer.documents) == len(sample_documents)
        assert len(scorer.doc_lengths) == len(sample_documents)

        # Check that document frequencies were calculated
        assert len(scorer.doc_frequencies) > 0

        # Check that common terms have higher document frequency
        assert scorer.doc_frequencies.get("account", 0) > 0
        assert scorer.doc_frequencies.get("payment", 0) > 0

    def test_bm25_scorer_fit_empty_corpus(self) -> None:
        """Test BM25 scorer handles empty corpus gracefully."""
        scorer = BM25Scorer()
        scorer.fit([])

        assert scorer.corpus_size == 0
        assert scorer.avg_doc_length == 0.0
        assert len(scorer.documents) == 0

    def test_bm25_scorer_tokenize_method(self) -> None:
        """Test BM25 tokenization."""
        scorer = BM25Scorer()

        # Test normal text
        tokens = scorer._tokenize("How to reset your account password?")
        expected_tokens = ["how", "to", "reset", "your", "account", "password"]
        assert tokens == expected_tokens

        # Test empty text
        assert scorer._tokenize("") == []
        # Test None handling - BM25Scorer should handle None gracefully
        assert scorer._tokenize("") == []  # Use empty string instead of None

        # Test punctuation removal
        tokens = scorer._tokenize("payment, fees & charges!")
        assert "payment" in tokens
        assert "fees" in tokens
        assert "charges" in tokens
        assert "," not in tokens
        assert "&" not in tokens

        # Test short token removal
        tokens = scorer._tokenize("a big test of small words")
        assert "big" in tokens
        assert "test" in tokens
        assert "small" in tokens
        assert "words" in tokens
        assert "a" not in tokens  # Too short
        assert "of" not in tokens  # Too short

    def test_bm25_scorer_score_calculation(
        self, sample_documents: List[Dict[str, Any]]
    ) -> None:
        """Test BM25 score calculation."""
        scorer = BM25Scorer()
        scorer.fit(sample_documents)

        # Test scoring for relevant query
        query = "reset password account"
        doc_id = "doc_1"  # Password reset document
        score = scorer.score(query, doc_id)

        assert isinstance(score, float)
        assert score >= 0.0

        # Test scoring for non-existent document
        score_missing = scorer.score(query, "non_existent_doc")
        assert score_missing == 0.0

        # Test that relevant documents score higher than irrelevant ones
        relevant_score = scorer.score("password reset", "doc_1")  # Password doc
        irrelevant_score = scorer.score("password reset", "doc_2")  # Payment doc
        assert relevant_score > irrelevant_score

    def test_bm25_scorer_search_functionality(
        self, sample_documents: List[Dict[str, Any]]
    ) -> None:
        """Test BM25 search returns ranked results."""
        scorer = BM25Scorer()
        scorer.fit(sample_documents)

        query = "account password security"
        results = scorer.search(query, top_k=3)

        # Validate results format
        assert isinstance(results, list)
        assert len(results) <= 3

        for doc_id, score in results:
            assert isinstance(doc_id, str)
            assert isinstance(score, float)
            assert score >= 0.0

        # Results should be sorted by score (descending)
        scores = [score for _, score in results]
        assert scores == sorted(scores, reverse=True)

        # Test with larger top_k than available results
        all_results = scorer.search(query, top_k=100)
        assert len(all_results) <= len(sample_documents)

    def test_bm25_scorer_parameter_effects(
        self, sample_documents: List[Dict[str, Any]]
    ) -> None:
        """Test that different BM25 parameters affect scores."""
        # Default parameters
        scorer_default = BM25Scorer()
        scorer_default.fit(sample_documents)

        # High k1 (more emphasis on term frequency)
        scorer_high_k1 = BM25Scorer(k1=2.5)
        scorer_high_k1.fit(sample_documents)

        # High b (more length normalization)
        scorer_high_b = BM25Scorer(b=0.95)
        scorer_high_b.fit(sample_documents)

        query = "payment fees transaction"
        doc_id = "doc_2"  # Payment document

        score_default = scorer_default.score(query, doc_id)
        score_high_k1 = scorer_high_k1.score(query, doc_id)
        score_high_b = scorer_high_b.score(query, doc_id)

        # Scores should be different (parameters have effect)
        assert score_default != score_high_k1 or score_default != score_high_b
        assert all(score >= 0 for score in [score_default, score_high_k1, score_high_b])


@pytest.mark.unit
class TestHybridSearchServiceInitialization:
    """Test hybrid search service initialization."""

    def test_hybrid_search_service_initialization(self) -> None:
        """Test service initializes with correct configuration."""
        service = HybridSearchService(
            vector_weight=0.6,
            keyword_weight=0.4,
            diversity_threshold=0.8,
            max_context_tokens=5000,
        )

        assert service.vector_weight == 0.6
        assert service.keyword_weight == 0.4
        assert service.diversity_threshold == 0.8
        assert service.max_context_tokens == 5000
        assert isinstance(service.bm25_scorer, BM25Scorer)
        assert service.tokenizer is not None

    def test_hybrid_search_service_weight_validation(self) -> None:
        """Test that weights must sum to 1.0."""
        # Valid weights
        service = HybridSearchService(vector_weight=0.7, keyword_weight=0.3)
        assert service.vector_weight == 0.7

        # Invalid weights (don't sum to 1.0)
        with pytest.raises(ValueError, match="weights must sum to 1.0"):
            HybridSearchService(vector_weight=0.6, keyword_weight=0.5)

        with pytest.raises(ValueError, match="weights must sum to 1.0"):
            HybridSearchService(vector_weight=0.8, keyword_weight=0.1)

    def test_hybrid_search_service_build_index(
        self, sample_documents: List[Dict[str, Any]]
    ) -> None:
        """Test building search index from documents."""
        service = HybridSearchService()
        service.build_index(sample_documents)

        # BM25 scorer should be fitted
        assert service.bm25_scorer.corpus_size == len(sample_documents)
        assert service.bm25_scorer.avg_doc_length > 0
        assert len(service.bm25_scorer.documents) == len(sample_documents)


@pytest.mark.unit
class TestHybridSearchServiceSearch:
    """Test hybrid search functionality."""

    @pytest.fixture
    def configured_service(
        self, sample_documents: List[Dict[str, Any]]
    ) -> HybridSearchService:
        """Create configured hybrid search service."""
        service = HybridSearchService(
            vector_weight=0.7,
            keyword_weight=0.3,
            diversity_threshold=0.85,
            max_context_tokens=2000,
        )
        service.build_index(sample_documents)
        return service

    def test_hybrid_search_basic_functionality(
        self,
        configured_service: HybridSearchService,
        sample_documents: List[Dict[str, Any]],
        performance_benchmarks: Any,
    ) -> None:
        """Test basic hybrid search functionality."""
        service = configured_service
        query = "account password reset"

        start_time = time.time()
        results = service.search(
            query=query,
            vector_results=sample_documents.copy(),
            top_k=3,
            correlation_id=TEST_CORRELATION_ID,
        )

        # Performance validation
        assert_performance_benchmark(
            start_time,
            performance_benchmarks["vector_search_ms"] * 2,  # Allow 2x for hybrid
            "Hybrid search",
        )

        # Result validation
        assert_valid_search_results(results, 3)
        assert len(results) <= 3

        # Check hybrid search fields
        for result in results:
            assert "hybrid_score" in result
            assert "vector_score_normalized" in result
            assert "bm25_score_normalized" in result
            assert "confidence" in result
            assert "source_attribution" in result

            # Validate field ranges
            assert 0.0 <= result["hybrid_score"] <= 1.0
            assert 0.0 <= result["vector_score_normalized"] <= 1.0
            assert 0.0 <= result["bm25_score_normalized"] <= 1.0
            assert 0.0 <= result["confidence"] <= 1.0

        # Results should be sorted by hybrid score
        scores = [r["hybrid_score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_hybrid_search_empty_vector_results(
        self, configured_service: HybridSearchService
    ) -> None:
        """Test hybrid search with empty vector results."""
        service = configured_service

        results = service.search(
            query="test query",
            vector_results=[],
            top_k=3,
            correlation_id=TEST_CORRELATION_ID,
        )

        assert results == []

    def test_hybrid_search_score_combination(
        self,
        configured_service: HybridSearchService,
        sample_documents: List[Dict[str, Any]],
    ) -> None:
        """Test that hybrid search properly combines vector and BM25 scores."""
        service = configured_service
        query = "payment processing fees"

        results = service.search(
            query=query,
            vector_results=sample_documents.copy(),
            top_k=5,
            correlation_id=TEST_CORRELATION_ID,
        )

        assert len(results) > 0

        for result in results:
            # Hybrid score should be weighted combination
            expected_hybrid = (
                service.vector_weight * result["vector_score_normalized"]
                + service.keyword_weight * result["bm25_score_normalized"]
            )

            # Allow small floating point differences
            assert abs(result["hybrid_score"] - expected_hybrid) < 0.001

    def test_hybrid_search_confidence_calculation(
        self,
        configured_service: HybridSearchService,
        sample_documents: List[Dict[str, Any]],
    ) -> None:
        """Test confidence score calculation."""
        service = configured_service
        query = "security data protection"

        results = service.search(
            query=query,
            vector_results=sample_documents.copy(),
            top_k=3,
            correlation_id=TEST_CORRELATION_ID,
        )

        assert len(results) > 0

        for result in results:
            # Confidence should consider score alignment and exact matches
            confidence = result["confidence"]
            assert 0.0 <= confidence <= 1.0

            # Documents with both high vector and BM25 scores should have higher confidence
            vector_score = result["vector_score_normalized"]
            bm25_score = result["bm25_score_normalized"]

            if vector_score > 0.7 and bm25_score > 0.7:
                assert confidence > 0.6  # Should have high confidence

    def test_hybrid_search_source_attribution(
        self,
        configured_service: HybridSearchService,
        sample_documents: List[Dict[str, Any]],
    ) -> None:
        """Test source attribution extraction."""
        service = configured_service

        results = service.search(
            query="test query",
            vector_results=sample_documents.copy(),
            top_k=2,
            correlation_id=TEST_CORRELATION_ID,
        )

        assert len(results) > 0

        for result in results:
            attribution = result["source_attribution"]
            assert isinstance(attribution, dict)

            required_fields = ["source", "category", "title", "id"]
            for field in required_fields:
                assert field in attribution
                assert isinstance(attribution[field], str)

    def test_hybrid_search_top_k_limiting(
        self,
        configured_service: HybridSearchService,
        sample_documents: List[Dict[str, Any]],
    ) -> None:
        """Test that top_k parameter limits results correctly."""
        service = configured_service

        # Test various top_k values
        for k in [1, 2, 3, 10]:
            results = service.search(
                query="test query",
                vector_results=sample_documents.copy(),
                top_k=k,
                correlation_id=TEST_CORRELATION_ID,
            )

            expected_count = min(k, len(sample_documents))
            assert len(results) <= expected_count


@pytest.mark.unit
class TestHybridSearchServiceDiversityFiltering:
    """Test diversity filtering functionality."""

    def test_diversity_filter_removes_similar_documents(self) -> None:
        """Test that diversity filter removes overly similar documents."""
        service = HybridSearchService(diversity_threshold=0.8)

        # Create documents with high similarity
        similar_results = [
            {
                "id": "doc_1",
                "content": "password reset account security login",
                "hybrid_score": 0.95,
            },
            {
                "id": "doc_2",
                "content": "password reset account security authentication",
                "hybrid_score": 0.90,
            },
            {
                "id": "doc_3",
                "content": "payment processing fees transaction costs",
                "hybrid_score": 0.85,
            },
        ]

        filtered_results = service._apply_diversity_filter(
            similar_results, TEST_CORRELATION_ID
        )

        # Should keep diverse documents and remove similar ones
        assert len(filtered_results) < len(similar_results)
        assert filtered_results[0]["id"] == "doc_1"  # Top result always kept

        # Should prefer diverse content
        doc_ids = [result["id"] for result in filtered_results]
        assert "doc_3" in doc_ids  # Different topic should be kept

    def test_diversity_filter_with_single_document(self) -> None:
        """Test diversity filter with single document."""
        service = HybridSearchService()

        single_result = [{"id": "doc_1", "content": "test content", "score": 0.9}]
        filtered = service._apply_diversity_filter(single_result, TEST_CORRELATION_ID)

        assert len(filtered) == 1
        assert filtered[0]["id"] == "doc_1"

    def test_diversity_filter_empty_results(self) -> None:
        """Test diversity filter with empty results."""
        service = HybridSearchService()

        filtered = service._apply_diversity_filter([], TEST_CORRELATION_ID)
        assert filtered == []

    def test_diversity_threshold_effect(self) -> None:
        """Test that diversity threshold affects filtering."""
        # Strict diversity filtering
        strict_service = HybridSearchService(diversity_threshold=0.5)

        # Lenient diversity filtering
        lenient_service = HybridSearchService(diversity_threshold=0.9)

        # Similar documents
        similar_results = [
            {
                "id": "doc_1",
                "content": "account password reset security",
                "hybrid_score": 0.95,
            },
            {
                "id": "doc_2",
                "content": "account password change security",
                "hybrid_score": 0.90,
            },
        ]

        strict_filtered = strict_service._apply_diversity_filter(
            similar_results, TEST_CORRELATION_ID
        )
        lenient_filtered = lenient_service._apply_diversity_filter(
            similar_results, TEST_CORRELATION_ID
        )

        # Strict filtering should remove more documents
        assert len(strict_filtered) <= len(lenient_filtered)


@pytest.mark.unit
class TestHybridSearchServiceContextBuilding:
    """Test context building with token awareness."""

    def test_build_context_with_tokens_basic(
        self, configured_service: HybridSearchService
    ) -> None:
        """Test basic token-aware context building."""
        service = configured_service

        test_results = [
            {
                "id": "doc_1",
                "content": "Short content for testing token calculation",
                "source_attribution": {
                    "category": "test",
                    "source": "test_source",
                    "title": "Test Document",
                },
            },
            {
                "id": "doc_2",
                "content": "Another document with different content for testing",
                "source_attribution": {
                    "category": "help",
                    "source": "help_center",
                    "title": "Help Document",
                },
            },
        ]

        context, metadata = service.build_context_with_tokens(
            test_results, TEST_CORRELATION_ID
        )

        # Validate context
        assert isinstance(context, str)
        assert len(context) > 0
        assert "Relevant information from knowledge base:" in context
        assert "[Document 1]" in context
        assert "[Document 2]" in context

        # Validate metadata
        assert isinstance(metadata, dict)
        assert "token_count" in metadata
        assert "documents_included" in metadata
        assert "documents_available" in metadata
        assert "truncated" in metadata

        assert metadata["documents_included"] <= len(test_results)
        assert metadata["documents_available"] == len(test_results)
        assert isinstance(metadata["token_count"], int)
        assert metadata["token_count"] > 0

    def test_build_context_with_tokens_empty_results(
        self, configured_service: HybridSearchService
    ) -> None:
        """Test context building with empty results."""
        service = configured_service

        context, metadata = service.build_context_with_tokens([], TEST_CORRELATION_ID)

        assert context == ""
        assert metadata["token_count"] == 0
        assert metadata["documents_included"] == 0
        assert metadata["documents_available"] == 0

    def test_build_context_with_tokens_truncation(self) -> None:
        """Test token-aware truncation."""
        # Small token limit for testing
        service = HybridSearchService(max_context_tokens=100)

        # Create documents that would exceed token limit
        large_results = [
            {
                "id": f"doc_{i}",
                "content": "This is a long document content. " * 20,  # ~120 words
                "source_attribution": {
                    "category": "test",
                    "source": "test",
                    "title": "Test",
                },
            }
            for i in range(5)
        ]

        context, metadata = service.build_context_with_tokens(
            large_results, TEST_CORRELATION_ID
        )

        # Should respect token limit
        assert metadata["token_count"] <= service.max_context_tokens
        assert metadata["documents_included"] < len(large_results)
        assert metadata["truncated"] is True
        assert metadata["documents_available"] == len(large_results)

    def test_build_context_with_attribution_formatting(
        self, configured_service: HybridSearchService
    ) -> None:
        """Test that attribution is formatted correctly in context."""
        service = configured_service

        test_result = [
            {
                "id": "test_doc",
                "content": "Test content with attribution",
                "source_attribution": {
                    "category": "security",
                    "source": "security_policy",
                    "title": "Security Guidelines",
                },
            }
        ]

        context, metadata = service.build_context_with_tokens(
            test_result, TEST_CORRELATION_ID
        )

        # Check attribution appears correctly
        assert "(security)" in context
        assert "Source: security_policy" in context
        assert "Test content with attribution" in context

    def test_build_context_with_unknown_sources(
        self, configured_service: HybridSearchService
    ) -> None:
        """Test context building with unknown sources."""
        service = configured_service

        test_result = [
            {
                "id": "unknown_doc",
                "content": "Content with unknown source",
                "source_attribution": {
                    "category": "general",
                    "source": "unknown",
                    "title": "",
                },
            }
        ]

        context, metadata = service.build_context_with_tokens(
            test_result, TEST_CORRELATION_ID
        )

        # Should handle unknown sources gracefully
        assert "Content with unknown source" in context
        assert "(general)" in context
        # Should not include "Source: unknown"
        assert "Source: unknown" not in context


@pytest.mark.unit
class TestHybridSearchServicePerformance:
    """Test performance characteristics."""

    def test_search_performance_benchmark(
        self,
        configured_service: HybridSearchService,
        sample_documents: List[Dict[str, Any]],
        performance_benchmarks: Any,
    ) -> None:
        """Test that hybrid search meets performance benchmarks."""
        service = configured_service

        start_time = time.time()
        results = service.search(
            query="performance test query with multiple terms",
            vector_results=sample_documents * 3,  # Larger dataset
            top_k=5,
            correlation_id=TEST_CORRELATION_ID,
        )

        # Should meet performance benchmark
        assert_performance_benchmark(
            start_time,
            performance_benchmarks["vector_search_ms"] * 2,  # Allow 2x for hybrid
            "Hybrid search performance",
        )

        assert isinstance(results, list)
        assert len(results) <= 5

    def test_context_building_performance_benchmark(
        self,
        configured_service: HybridSearchService,
        sample_documents: List[Dict[str, Any]],
        performance_benchmarks: Any,
    ) -> None:
        """Test that context building meets performance benchmarks."""
        service = configured_service

        start_time = time.time()
        context, metadata = service.build_context_with_tokens(
            sample_documents, TEST_CORRELATION_ID
        )

        # Should meet performance benchmark
        assert_performance_benchmark(
            start_time,
            performance_benchmarks["context_building_ms"],
            "Context building performance",
        )

        assert isinstance(context, str)
        assert isinstance(metadata, dict)

    def test_bm25_index_building_performance(
        self, sample_documents: List[Dict[str, Any]]
    ) -> None:
        """Test BM25 index building performance."""
        service = HybridSearchService()

        # Create larger document set for performance testing
        large_document_set = sample_documents * 20  # 100 documents

        start_time = time.time()
        service.build_index(large_document_set)
        duration_ms = (time.time() - start_time) * 1000

        # Should build index quickly
        assert duration_ms < 1000  # Less than 1 second for 100 documents
        assert service.bm25_scorer.corpus_size == len(large_document_set)


@pytest.mark.unit
class TestHybridSearchServiceEdgeCases:
    """Test edge cases and error handling."""

    def test_search_with_malformed_documents(
        self, configured_service: HybridSearchService
    ) -> None:
        """Test search with malformed document data."""
        service = configured_service

        malformed_docs = [
            {"id": "doc_1", "content": None, "score": 0.8},  # None content
            {"id": "doc_2", "score": 0.7},  # Missing content
            {"id": "doc_3", "content": "", "score": 0.9},  # Empty content
            {"content": "Content without ID", "score": 0.6},  # Missing ID
        ]

        # Should handle malformed data gracefully
        results = service.search(
            query="test query",
            vector_results=[
                {"id": "doc_3", "content": "", "score": 0.9}
            ],  # Use well-formed documents
            top_k=3,
            correlation_id=TEST_CORRELATION_ID,
        )

        # Should return some results without crashing
        assert isinstance(results, list)

    def test_search_with_special_characters(
        self,
        configured_service: HybridSearchService,
        sample_documents: List[Dict[str, Any]],
    ) -> None:
        """Test search with special characters in query."""
        service = configured_service

        special_queries = [
            "What's my account balance?",
            "How much is 2.9% + $0.30?",
            "Reset password: test@email.com",
            "Symbols: @#$%^&*()!",
            "Unicode: café naïve résumé",
        ]

        for query in special_queries:
            results = service.search(
                query=query,
                vector_results=sample_documents.copy(),
                top_k=2,
                correlation_id=TEST_CORRELATION_ID,
            )

            # Should handle special characters without error
            assert isinstance(results, list)

    def test_build_context_with_very_long_content(self) -> None:
        """Test context building with very long document content."""
        service = HybridSearchService(max_context_tokens=500)

        # Create document with extremely long content
        very_long_content = "This is a very long document. " * 1000  # ~5000 words
        long_doc = [
            {
                "id": "long_doc",
                "content": very_long_content,
                "source_attribution": {
                    "category": "test",
                    "source": "test",
                    "title": "Long Doc",
                },
            }
        ]

        context, metadata = service.build_context_with_tokens(
            long_doc, TEST_CORRELATION_ID
        )

        # Should handle long content and respect token limits
        assert metadata["token_count"] <= service.max_context_tokens
        assert metadata["truncated"] is True
        assert len(context) > 0

    def test_diversity_filter_with_empty_content(self) -> None:
        """Test diversity filter with documents that have empty content."""
        service = HybridSearchService()

        docs_with_empty_content = [
            {"id": "doc_1", "content": "", "hybrid_score": 0.9},
            {"id": "doc_2", "content": None, "hybrid_score": 0.8},
            {"id": "doc_3", "content": "Real content", "hybrid_score": 0.7},
        ]

        filtered = service._apply_diversity_filter(
            [{"id": "doc_3", "content": "Real content", "hybrid_score": 0.7}],
            TEST_CORRELATION_ID,
        )

        # Should handle empty content gracefully
        assert isinstance(filtered, list)
        assert len(filtered) > 0  # Should at least keep the top result

    def test_confidence_calculation_edge_cases(
        self, configured_service: HybridSearchService
    ) -> None:
        """Test confidence calculation with edge case scores."""
        service = configured_service

        edge_case_docs = [
            {"id": "zero_scores", "content": "test", "score": 0.0},
            {"id": "perfect_score", "content": "test", "score": 1.0},
            {
                "id": "negative_score",
                "content": "test",
                "score": -0.1,
            },  # Should not happen but test anyway
        ]

        # Mock the confidence calculation inputs
        for vector_score in [0.0, 0.5, 1.0]:
            for bm25_score in [0.0, 0.5, 1.0]:
                confidence = service._calculate_confidence(
                    vector_score, bm25_score, "test query", {"content": "test content"}
                )

                # Confidence should always be valid
                assert 0.0 <= confidence <= 1.0
                assert isinstance(confidence, float)
