"""
Validation tests for hybrid search system comparing performance against vector-only search.

Tests relevance improvements, diversity filtering, and context window management
for fintech FAQ retrieval scenarios.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List

import pytest

from app.services.hybrid_search_service import BM25Scorer, HybridSearchService

logger = logging.getLogger(__name__)


class HybridSearchValidator:
    """Validator for hybrid search system performance and quality."""

    def __init__(self) -> None:
        """Initialize validator with test data and services."""
        self.test_queries = [
            {
                "query": "How do I reset my account password?",
                "expected_categories": ["account", "security"],
                "expected_keywords": ["password", "reset", "account"],
            },
            {
                "query": "What are the payment processing fees?",
                "expected_categories": ["payment", "billing"],
                "expected_keywords": ["payment", "fees", "processing"],
            },
            {
                "query": "How long does a bank transfer take?",
                "expected_categories": ["payment", "transfer"],
                "expected_keywords": ["bank", "transfer", "time"],
            },
            {
                "query": "Is my financial data secure?",
                "expected_categories": ["security", "compliance"],
                "expected_keywords": ["secure", "data", "financial"],
            },
            {
                "query": "How to upgrade my business account?",
                "expected_categories": ["account", "business"],
                "expected_keywords": ["upgrade", "business", "account"],
            },
        ]

        self.mock_documents = self._create_mock_documents()

    def _create_mock_documents(self) -> List[Dict[str, Any]]:
        """Create mock fintech FAQ documents for testing."""
        return [
            {
                "id": "doc_1",
                "content": "To reset your account password, go to login page and click 'Forgot Password'. Enter your email address and follow the instructions sent to your inbox.",
                "category": "account",
                "source": "help_center",
                "title": "Password Reset Instructions",
                "score": 0.85,
            },
            {
                "id": "doc_2",
                "content": "Our payment processing fees are 2.9% + $0.30 per transaction for credit cards. Bank transfers have a flat fee of $1.50 per transaction.",
                "category": "payment",
                "source": "pricing_guide",
                "title": "Payment Processing Fees",
                "score": 0.78,
            },
            {
                "id": "doc_3",
                "content": "Standard bank transfers typically take 1-3 business days to complete. Express transfers can be processed within 24 hours for an additional fee.",
                "category": "payment",
                "source": "help_center",
                "title": "Bank Transfer Timeline",
                "score": 0.82,
            },
            {
                "id": "doc_4",
                "content": "Your financial data is protected using bank-level encryption and secure servers. We comply with PCI DSS and SOC 2 Type II standards.",
                "category": "security",
                "source": "security_policy",
                "title": "Data Security Measures",
                "score": 0.90,
            },
            {
                "id": "doc_5",
                "content": "Business account upgrades include additional features like bulk payments, advanced reporting, and priority support. Contact sales for pricing.",
                "category": "account",
                "source": "business_guide",
                "title": "Business Account Features",
                "score": 0.75,
            },
            {
                "id": "doc_6",
                "content": "Password security best practices: use strong passwords with mix of letters, numbers and symbols. Enable two-factor authentication for extra security.",
                "category": "security",
                "source": "security_guide",
                "title": "Password Security Tips",
                "score": 0.72,
            },
            {
                "id": "doc_7",
                "content": "Account verification requires government-issued ID and proof of address. Business accounts also need business registration documents.",
                "category": "account",
                "source": "verification_guide",
                "title": "Account Verification Requirements",
                "score": 0.68,
            },
            {
                "id": "doc_8",
                "content": "International wire transfers may take 3-5 business days and incur additional correspondent bank fees. Check with your bank for exact timing.",
                "category": "payment",
                "source": "international_guide",
                "title": "International Transfer Information",
                "score": 0.70,
            },
        ]

    async def validate_bm25_scoring(self) -> Dict[str, Any]:
        """Validate BM25 scoring algorithm performance."""
        logger.info("Validating BM25 scoring algorithm")

        # Initialize BM25 scorer
        bm25_scorer = BM25Scorer()
        bm25_scorer.fit(self.mock_documents)

        results: Dict[str, Any] = {
            "test_name": "BM25 Scoring Validation",
            "query_tests": [],
            "overall_score": 0.0,
        }

        for test_case in self.test_queries:
            query = str(test_case["query"])
            expected_keywords = test_case["expected_keywords"]

            # Get BM25 scores for all documents
            bm25_results = bm25_scorer.search(query, top_k=len(self.mock_documents))

            # Validate that documents with expected keywords rank higher
            keyword_matches: List[Dict[str, Any]] = []
            for doc_id, score in bm25_results[:3]:  # Top 3 results
                doc = next((d for d in self.mock_documents if d["id"] == doc_id), None)
                if doc:
                    content_lower = doc["content"].lower()
                    matched_keywords = [
                        kw for kw in expected_keywords if kw in content_lower
                    ]
                    keyword_matches.append(
                        {
                            "doc_id": doc_id,
                            "score": score,
                            "matched_keywords": matched_keywords,
                            "match_ratio": len(matched_keywords)
                            / len(expected_keywords),
                        }
                    )

            avg_match_ratio = (
                sum(float(km["match_ratio"]) for km in keyword_matches)
                / len(keyword_matches)
                if keyword_matches
                else 0.0
            )

            query_result = {
                "query": query,
                "top_matches": keyword_matches,
                "avg_keyword_match_ratio": avg_match_ratio,
                "passed": avg_match_ratio
                > 0.5,  # At least 50% keyword matching in top results
            }

            query_tests = results["query_tests"]
            assert isinstance(query_tests, list)
            query_tests.append(query_result)

        # Calculate overall score
        query_tests = results["query_tests"]
        assert isinstance(query_tests, list)
        passed_tests = sum(1 for qt in query_tests if qt["passed"])
        results["overall_score"] = passed_tests / len(query_tests)
        results["passed"] = results["overall_score"] >= 0.8  # 80% pass rate

        logger.info(
            f"BM25 validation completed: {results['overall_score']:.2%} pass rate"
        )
        return results

    async def validate_hybrid_vs_vector_only(self) -> Dict[str, Any]:
        """Compare hybrid search results against vector-only search."""
        logger.info("Comparing hybrid search vs vector-only search")

        # Initialize hybrid search service
        hybrid_service = HybridSearchService(
            vector_weight=0.7, keyword_weight=0.3, diversity_threshold=0.85
        )
        hybrid_service.build_index(self.mock_documents)

        results: Dict[str, Any] = {
            "test_name": "Hybrid vs Vector-Only Comparison",
            "query_comparisons": [],
            "hybrid_advantages": 0,
            "vector_advantages": 0,
            "ties": 0,
        }

        for test_case in self.test_queries:
            query = str(test_case["query"])
            expected_categories = test_case["expected_categories"]
            assert isinstance(expected_categories, list)

            # Simulate vector-only results (sorted by vector score)
            vector_only_results = sorted(
                self.mock_documents, key=lambda x: x["score"], reverse=True
            )[:5]

            # Get hybrid search results
            hybrid_results = hybrid_service.search(
                query=query, vector_results=self.mock_documents.copy(), top_k=5
            )

            # Evaluate relevance for both approaches
            vector_relevance = self._calculate_relevance_score(
                vector_only_results, expected_categories
            )
            hybrid_relevance = self._calculate_relevance_score(
                hybrid_results, expected_categories
            )

            # Evaluate diversity
            vector_diversity = self._calculate_diversity_score(vector_only_results)
            hybrid_diversity = self._calculate_diversity_score(hybrid_results)

            comparison_result: Dict[str, Any] = {
                "query": query,
                "vector_only": {
                    "relevance_score": vector_relevance,
                    "diversity_score": vector_diversity,
                    "total_score": vector_relevance * 0.7 + vector_diversity * 0.3,
                    "top_docs": [doc["id"] for doc in vector_only_results[:3]],
                },
                "hybrid": {
                    "relevance_score": hybrid_relevance,
                    "diversity_score": hybrid_diversity,
                    "total_score": hybrid_relevance * 0.7 + hybrid_diversity * 0.3,
                    "top_docs": [doc["id"] for doc in hybrid_results[:3]],
                },
            }

            # Determine winner
            hybrid_score = float(comparison_result["hybrid"]["total_score"])
            vector_score = float(comparison_result["vector_only"]["total_score"])

            if hybrid_score > vector_score:
                comparison_result["winner"] = "hybrid"
                results["hybrid_advantages"] = int(results["hybrid_advantages"]) + 1
            elif vector_score > hybrid_score:
                comparison_result["winner"] = "vector_only"
                results["vector_advantages"] = int(results["vector_advantages"]) + 1
            else:
                comparison_result["winner"] = "tie"
                results["ties"] = int(results["ties"]) + 1

            query_comparisons = results["query_comparisons"]
            assert isinstance(query_comparisons, list)
            query_comparisons.append(comparison_result)

        # Calculate overall performance
        total_queries = len(self.test_queries)
        hybrid_advantages = int(results["hybrid_advantages"])
        results["hybrid_win_rate"] = hybrid_advantages / total_queries
        results["passed"] = (
            results["hybrid_win_rate"] >= 0.6
        )  # Hybrid should win at least 60% of the time

        logger.info(
            f"Hybrid vs vector-only completed: hybrid wins {results['hybrid_win_rate']:.2%} of queries"
        )
        return results

    async def validate_diversity_filtering(self) -> Dict[str, Any]:
        """Validate diversity filtering prevents overly similar results."""
        logger.info("Validating diversity filtering")

        # Create documents with high similarity for testing
        similar_docs = [
            {
                "id": "sim_1",
                "content": "Password reset instructions for your account security and login access",
                "category": "account",
                "score": 0.95,
            },
            {
                "id": "sim_2",
                "content": "How to reset password and secure your account login credentials",
                "category": "account",
                "score": 0.93,
            },
            {
                "id": "sim_3",
                "content": "Account password reset guide for secure login authentication",
                "category": "account",
                "score": 0.91,
            },
            {
                "id": "diff_1",
                "content": "Payment processing fees and transaction costs for business accounts",
                "category": "payment",
                "score": 0.85,
            },
        ]

        hybrid_service = HybridSearchService(
            vector_weight=0.7,
            keyword_weight=0.3,
            diversity_threshold=0.85,  # High threshold for testing
        )
        hybrid_service.build_index(similar_docs)

        # Test with query that would return similar documents
        results = hybrid_service.search(
            query="password reset account", vector_results=similar_docs, top_k=4
        )

        # Check diversity - should have filtered out some similar documents
        unique_categories = set(doc.get("category") for doc in results)
        content_diversity = len(
            set(doc.get("content", "").split()[:5] for doc in results)
        )

        validation_result = {
            "test_name": "Diversity Filtering Validation",
            "original_docs": len(similar_docs),
            "filtered_results": len(results),
            "unique_categories": len(unique_categories),
            "content_diversity_score": (
                content_diversity / len(results) if results else 0
            ),
            "diversity_applied": len(results) < len(similar_docs),
            "passed": len(unique_categories) > 1
            or content_diversity > 2,  # Should have diverse results
        }

        logger.info(
            f"Diversity filtering validation: {'PASSED' if validation_result['passed'] else 'FAILED'}"
        )
        return validation_result

    async def validate_context_window_management(self) -> Dict[str, Any]:
        """Validate token-aware context window management."""
        logger.info("Validating context window management")

        # Create documents with varying lengths
        long_docs = []
        for i in range(10):
            content = f"This is document {i+1}. " + (
                "Long content with many words. " * 50
            )  # ~300 words each
            long_docs.append(
                {
                    "id": f"long_doc_{i+1}",
                    "content": content,
                    "category": "test",
                    "score": 0.8 - (i * 0.05),  # Decreasing scores
                }
            )

        hybrid_service = HybridSearchService(
            max_context_tokens=1000  # Small limit for testing
        )

        # Build context with token awareness
        context, metadata = hybrid_service.build_context_with_tokens(long_docs)

        validation_result = {
            "test_name": "Context Window Management Validation",
            "total_documents": len(long_docs),
            "documents_included": metadata["documents_included"],
            "estimated_tokens": metadata["token_count"],
            "truncated": metadata["truncated"],
            "token_limit": hybrid_service.max_context_tokens,
            "within_limit": metadata["token_count"]
            <= hybrid_service.max_context_tokens,
            "context_length": len(context),
            "passed": metadata["token_count"] <= hybrid_service.max_context_tokens
            and metadata["documents_included"] > 0,
        }

        logger.info(
            f"Context window validation: {validation_result['documents_included']}/{validation_result['total_documents']} docs, {validation_result['estimated_tokens']} tokens"
        )
        return validation_result

    def _calculate_relevance_score(
        self, documents: List[Dict[str, Any]], expected_categories: List[str]
    ) -> float:
        """Calculate relevance score based on category matching."""
        if not documents:
            return 0.0

        relevant_docs = 0
        for doc in documents:
            doc_category = doc.get("category", "")
            if doc_category in expected_categories:
                relevant_docs += 1

        return relevant_docs / len(documents)

    def _calculate_diversity_score(self, documents: List[Dict[str, Any]]) -> float:
        """Calculate diversity score based on unique categories and content."""
        if not documents:
            return 0.0

        categories = set(doc.get("category") for doc in documents)
        category_diversity = len(categories) / len(documents)

        # Simple content diversity based on unique first words
        first_words = set(
            doc.get("content", "").split()[0].lower()
            for doc in documents
            if doc.get("content")
        )
        content_diversity = len(first_words) / len(documents)

        return (category_diversity + content_diversity) / 2

    async def run_full_validation(self) -> Dict[str, Any]:
        """Run complete validation suite for hybrid search system."""
        logger.info("Starting full hybrid search validation suite")

        validation_results: Dict[str, Any] = {
            "validation_suite": "Hybrid Search System Validation",
            "timestamp": "2024-01-01T00:00:00Z",  # Would be actual timestamp
            "tests": [],
        }

        # Run all validation tests
        test_methods = [
            self.validate_bm25_scoring,
            self.validate_hybrid_vs_vector_only,
            self.validate_diversity_filtering,
            self.validate_context_window_management,
        ]

        for test_method in test_methods:
            try:
                test_result = await test_method()
                tests_list = validation_results["tests"]
                assert isinstance(tests_list, list)
                tests_list.append(test_result)
            except Exception as e:
                logger.error(f"Test {test_method.__name__} failed: {str(e)}")
                tests_list = validation_results["tests"]
                assert isinstance(tests_list, list)
                tests_list.append(
                    {
                        "test_name": test_method.__name__,
                        "error": str(e),
                        "passed": False,
                    }
                )

        # Calculate overall validation score
        tests_list = validation_results["tests"]
        assert isinstance(tests_list, list)
        passed_tests = sum(
            1
            for test in tests_list
            if isinstance(test, dict) and test.get("passed", False)
        )
        total_tests = len(tests_list)

        validation_results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "overall_pass_rate": passed_tests / total_tests if total_tests > 0 else 0.0,
            "validation_passed": (
                passed_tests / total_tests >= 0.75 if total_tests > 0 else False
            ),  # 75% pass rate required
        }

        logger.info(
            f"Validation suite completed: {validation_results['summary']['overall_pass_rate']:.2%} pass rate"
        )
        return validation_results


# Pytest test cases for automated validation
@pytest.mark.asyncio
async def test_hybrid_search_validation() -> None:
    """Test hybrid search system meets all acceptance criteria."""
    validator = HybridSearchValidator()
    results = await validator.run_full_validation()

    # Assert overall validation passes
    assert results["summary"][
        "validation_passed"
    ], f"Validation failed with {results['summary']['overall_pass_rate']:.2%} pass rate"

    # Assert specific test results
    tests_list = results["tests"]
    assert isinstance(tests_list, list)
    test_results = {
        test["test_name"]: test
        for test in tests_list
        if isinstance(test, dict) and "test_name" in test
    }

    # BM25 scoring should work correctly
    assert "BM25 Scoring Validation" in test_results
    assert test_results["BM25 Scoring Validation"][
        "passed"
    ], "BM25 scoring validation failed"

    # Hybrid search should outperform vector-only
    assert "Hybrid vs Vector-Only Comparison" in test_results
    assert test_results["Hybrid vs Vector-Only Comparison"][
        "passed"
    ], "Hybrid search did not outperform vector-only"

    # Diversity filtering should work
    assert "Diversity Filtering Validation" in test_results
    assert test_results["Diversity Filtering Validation"][
        "passed"
    ], "Diversity filtering validation failed"

    # Context window management should work
    assert "Context Window Management Validation" in test_results
    assert test_results["Context Window Management Validation"][
        "passed"
    ], "Context window management validation failed"


if __name__ == "__main__":
    """Run validation suite standalone."""

    async def main() -> None:
        validator = HybridSearchValidator()
        results = await validator.run_full_validation()
        print(json.dumps(results, indent=2))

    asyncio.run(main())
