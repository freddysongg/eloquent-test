"""
Test configuration and fixtures for EloquentAI backend test suite.

Provides comprehensive test fixtures for RAG pipeline, external service mocking,
and test utilities for unit, integration, and performance testing.
"""

import asyncio
import logging
import os
import time
from typing import Any, Dict, Generator, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pytest

from app.core.resilience import CircuitBreakerConfig, ResilienceManager, RetryConfig
from app.integrations.pinecone_client import PineconeClient
from app.services.hybrid_search_service import HybridSearchService
from app.services.rag_service import RAGService

# Configure logging for tests
logging.getLogger().setLevel(logging.INFO)

# Test configuration
TEST_EMBEDDING_DIMENSIONS = 1024
TEST_CORRELATION_ID = "test-correlation-123"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings() -> Mock:
    """Mock settings with test configuration."""
    mock_settings = Mock()
    mock_settings.PINECONE_API_KEY = "test-api-key"
    mock_settings.PINECONE_INDEX_NAME = "test-index"
    mock_settings.PINECONE_INDEX_HOST = "https://test.pinecone.io"
    mock_settings.EMBEDDING_MODEL = "llama-text-embed-v2"
    mock_settings.EMBEDDING_DIMENSIONS = TEST_EMBEDDING_DIMENSIONS
    mock_settings.EMBEDDING_CACHE_TTL_SECONDS = 3600
    mock_settings.EMBEDDING_REQUEST_TIMEOUT_SECONDS = 30.0
    mock_settings.OPENAI_API_KEY = "test-openai-key"
    mock_settings.OPENAI_EMBEDDING_MODEL = "text-embedding-3-large"
    mock_settings.REDIS_URL = "redis://localhost:6379/1"
    return mock_settings


@pytest.fixture
def sample_documents() -> List[Dict[str, Any]]:
    """Sample fintech FAQ documents for testing."""
    return [
        {
            "id": "doc_1",
            "content": "To reset your account password, go to login page and click 'Forgot Password'. Enter your email address and follow the instructions sent to your inbox.",
            "category": "account",
            "source": "help_center",
            "title": "Password Reset Instructions",
            "score": 0.85,
            "metadata": {
                "category": "account",
                "source": "help_center",
                "title": "Password Reset Instructions",
            },
        },
        {
            "id": "doc_2",
            "content": "Our payment processing fees are 2.9% + $0.30 per transaction for credit cards. Bank transfers have a flat fee of $1.50 per transaction.",
            "category": "payment",
            "source": "pricing_guide",
            "title": "Payment Processing Fees",
            "score": 0.78,
            "metadata": {
                "category": "payment",
                "source": "pricing_guide",
                "title": "Payment Processing Fees",
            },
        },
        {
            "id": "doc_3",
            "content": "Your financial data is protected using bank-level encryption and secure servers. We comply with PCI DSS and SOC 2 Type II standards.",
            "category": "security",
            "source": "security_policy",
            "title": "Data Security Measures",
            "score": 0.90,
            "metadata": {
                "category": "security",
                "source": "security_policy",
                "title": "Data Security Measures",
            },
        },
        {
            "id": "doc_4",
            "content": "Business account upgrades include additional features like bulk payments, advanced reporting, and priority support. Contact sales for pricing.",
            "category": "account",
            "source": "business_guide",
            "title": "Business Account Features",
            "score": 0.75,
            "metadata": {
                "category": "account",
                "source": "business_guide",
                "title": "Business Account Features",
            },
        },
        {
            "id": "doc_5",
            "content": "Standard bank transfers typically take 1-3 business days to complete. Express transfers can be processed within 24 hours for an additional fee.",
            "category": "payment",
            "source": "help_center",
            "title": "Bank Transfer Timeline",
            "score": 0.82,
            "metadata": {
                "category": "payment",
                "source": "help_center",
                "title": "Bank Transfer Timeline",
            },
        },
    ]


@pytest.fixture
def sample_embeddings() -> List[List[float]]:
    """Sample embeddings for test documents."""
    embeddings = []
    for i in range(5):  # Match number of sample documents
        # Create deterministic but realistic embeddings
        np.random.seed(i + 42)  # Different seed for each document
        embedding = np.random.normal(0, 0.1, TEST_EMBEDDING_DIMENSIONS).tolist()
        # Normalize to unit vector
        magnitude = np.linalg.norm(embedding)
        embedding = [x / magnitude for x in embedding]
        embeddings.append(embedding)
    return embeddings


@pytest.fixture
def test_query_embedding() -> List[float]:
    """Sample query embedding for testing."""
    np.random.seed(100)
    embedding = np.random.normal(0, 0.1, TEST_EMBEDDING_DIMENSIONS).tolist()
    magnitude = np.linalg.norm(embedding)
    return [x / magnitude for x in embedding]


class MockPineconeResponse:
    """Mock Pinecone API response."""

    def __init__(self, matches: List[Dict[str, Any]]):
        self.matches = [MockPineconeMatch(**match) for match in matches]


class MockPineconeMatch:
    """Mock Pinecone match object."""

    def __init__(
        self, id: str, score: float, metadata: Dict[str, Any], **kwargs: Any
    ) -> None:
        self.id = id
        self.score = score
        self.metadata = metadata


class MockPineconeInferenceResponse:
    """Mock Pinecone Inference API response."""

    def __init__(self, embedding: List[float]):
        self.data = [MockEmbeddingData(embedding)]


class MockEmbeddingData:
    """Mock embedding data."""

    def __init__(self, values: List[float]):
        self.values = values


@pytest.fixture
def mock_pinecone_client(
    sample_documents: List[Dict[str, Any]], sample_embeddings: List[List[float]]
) -> AsyncMock:
    """Mock Pinecone client for testing."""
    mock_client = AsyncMock(spec=PineconeClient)

    # Mock search_documents method
    async def mock_search(
        query_embedding: List[float], top_k: int = 5, **kwargs: Any
    ) -> List[Dict[str, Any]]:
        # Return sample documents sorted by score
        results = sorted(sample_documents, key=lambda x: x["score"], reverse=True)[
            :top_k
        ]
        return results

    mock_client.search_documents = AsyncMock(side_effect=mock_search)

    # Mock embed_text method
    async def mock_embed_text(text: str, correlation_id: str = "") -> List[float]:
        # Return deterministic embedding based on text hash
        text_hash = hash(text) % len(sample_embeddings)
        return sample_embeddings[text_hash]

    mock_client.embed_text = AsyncMock(side_effect=mock_embed_text)

    # Mock other methods
    mock_client.get_index_stats = AsyncMock(
        return_value={
            "total_vector_count": len(sample_documents),
            "dimension": TEST_EMBEDDING_DIMENSIONS,
            "index_fullness": 0.1,
            "namespaces": {},
        }
    )

    mock_client.health_check = AsyncMock(
        return_value={
            "service": "pinecone",
            "status": "healthy",
            "checks": {"connectivity": {"status": "healthy"}},
            "circuit_breakers": {},
            "timestamp": time.time(),
        }
    )

    mock_client.calculate_relevance_score = Mock(
        side_effect=lambda score, metadata: min(score * 1.1, 1.0)
    )

    return mock_client


class MockRedisClient:
    """Mock Redis client for testing."""

    def __init__(self) -> None:
        self.data: Dict[str, Any] = {}
        self.expirations: Dict[str, float] = {}

    async def get_json(self, key: str, correlation_id: str = "") -> Optional[Any]:
        """Mock get JSON data."""
        if key in self.data and not self._is_expired(key):
            return self.data[key]
        return None

    async def set_json(
        self, key: str, value: Any, expiration: int = 300, correlation_id: str = ""
    ) -> None:
        """Mock set JSON data."""
        self.data[key] = value
        if expiration:
            self.expirations[key] = time.time() + expiration

    async def get_keys_by_pattern(
        self, pattern: str, correlation_id: str = ""
    ) -> List[str]:
        """Mock key pattern matching."""
        import fnmatch

        matching_keys = []
        for key in self.data.keys():
            if fnmatch.fnmatch(key, pattern):
                matching_keys.append(key)
        return matching_keys

    def _is_expired(self, key: str) -> bool:
        """Check if key is expired."""
        if key in self.expirations:
            return time.time() > self.expirations[key]
        return False

    def clear(self) -> None:
        """Clear all data."""
        self.data.clear()
        self.expirations.clear()


@pytest.fixture
def mock_redis_client() -> MockRedisClient:
    """Mock Redis client fixture."""
    return MockRedisClient()


@pytest.fixture
def mock_get_redis_client(mock_redis_client: MockRedisClient) -> AsyncMock:
    """Mock get_redis_client function."""

    async def _get_redis_client() -> MockRedisClient:
        return mock_redis_client

    return AsyncMock(side_effect=_get_redis_client)


@pytest.fixture
def mock_resilience_manager() -> ResilienceManager:
    """Mock resilience manager with test configurations."""
    manager = ResilienceManager()

    # Override with test configurations (faster timeouts)
    test_configs: Dict[str, Dict[str, Any]] = {
        "pinecone": {
            "cb_config": CircuitBreakerConfig(
                failure_threshold=2,
                recovery_timeout=1,  # 1 second for tests
                success_threshold=1,
                timeout_seconds=5.0,
            ),
            "retry_config": RetryConfig(
                max_attempts=2, base_delay=0.1, max_delay=1.0  # 100ms for tests
            ),
        },
        "embedding_api": {
            "cb_config": CircuitBreakerConfig(
                failure_threshold=2,
                recovery_timeout=1,
                success_threshold=1,
                timeout_seconds=5.0,
            ),
            "retry_config": RetryConfig(max_attempts=2, base_delay=0.1, max_delay=1.0),
        },
    }

    for service_name, config in test_configs.items():
        cb_config = config["cb_config"]
        retry_config = config["retry_config"]
        manager.register_service(service_name, cb_config, retry_config)

    return manager


@pytest.fixture
def rag_service_with_mocks(
    mock_pinecone_client: AsyncMock,
    mock_get_redis_client: AsyncMock,
    mock_resilience_manager: ResilienceManager,
) -> RAGService:
    """RAG service with mocked dependencies."""
    with (
        patch(
            "app.services.rag_service.PineconeClient", return_value=mock_pinecone_client
        ),
        patch("app.services.rag_service.get_redis_client", mock_get_redis_client),
        patch("app.core.resilience.resilience_manager", mock_resilience_manager),
    ):
        service = RAGService()
        service.pinecone_client = mock_pinecone_client
        return service


@pytest.fixture
def hybrid_search_service(
    sample_documents: List[Dict[str, Any]]
) -> HybridSearchService:
    """Hybrid search service with test configuration."""
    service = HybridSearchService(
        vector_weight=0.7,
        keyword_weight=0.3,
        diversity_threshold=0.85,
        max_context_tokens=2000,  # Smaller for tests
    )
    service.build_index(sample_documents)
    return service


@pytest.fixture
def performance_benchmarks() -> Dict[str, float]:
    """Performance benchmarks for testing."""
    return {
        "embedding_generation_ms": 500.0,  # 500ms max for embedding
        "vector_search_ms": 200.0,  # 200ms max for search
        "rag_query_ms": 500.0,  # 500ms max for full query
        "context_building_ms": 100.0,  # 100ms max for context building
        "relevance_threshold": 0.85,  # 85% relevance accuracy
    }


@pytest.fixture(autouse=True)
def cleanup_after_test() -> Generator[None, None, None]:
    """Cleanup after each test."""
    yield


class TestDataFactory:
    """Factory for creating test data."""

    @staticmethod
    def create_query_test_case(
        query: str, expected_categories: List[str]
    ) -> Dict[str, Any]:
        """Create test case for query testing."""
        return {
            "query": query,
            "expected_categories": expected_categories,
            "expected_keywords": query.lower().split(),
            "correlation_id": f"test-{hash(query) % 10000}",
        }

    @staticmethod
    def create_performance_test_case(
        operation: str, max_duration_ms: float
    ) -> Dict[str, Any]:
        """Create performance test case."""
        return {
            "operation": operation,
            "max_duration_ms": max_duration_ms,
            "start_time": time.time(),
        }

    @staticmethod
    def create_error_scenario(
        error_type: str, should_retry: bool = True
    ) -> Dict[str, Any]:
        """Create error scenario for testing."""
        return {
            "error_type": error_type,
            "should_retry": should_retry,
            "correlation_id": f"error-test-{int(time.time())}",
        }


# Utility functions for testing
def assert_valid_embedding(
    embedding: List[float], expected_dimensions: int = TEST_EMBEDDING_DIMENSIONS
) -> None:
    """Assert that embedding is valid."""
    assert isinstance(embedding, list), "Embedding should be a list"
    assert (
        len(embedding) == expected_dimensions
    ), f"Embedding should have {expected_dimensions} dimensions"
    assert all(
        isinstance(x, (int, float)) for x in embedding
    ), "All embedding values should be numeric"

    # Check if normalized (unit vector)
    magnitude = np.linalg.norm(embedding)
    assert (
        0.9 <= magnitude <= 1.1
    ), f"Embedding should be approximately normalized, got magnitude {magnitude}"


def assert_valid_search_results(
    results: List[Dict[str, Any]], max_count: Optional[int] = None
) -> None:
    """Assert that search results are valid."""
    assert isinstance(results, list), "Results should be a list"
    if max_count:
        assert len(results) <= max_count, f"Results should not exceed {max_count}"

    for result in results:
        assert "id" in result, "Result should have id"
        assert "content" in result, "Result should have content"
        assert "score" in result or "hybrid_score" in result, "Result should have score"
        assert isinstance(result.get("metadata", {}), dict), "Metadata should be a dict"


def assert_performance_benchmark(
    start_time: float, max_duration_ms: float, operation: str = ""
) -> None:
    """Assert that operation meets performance benchmark."""
    duration_ms = (time.time() - start_time) * 1000
    assert (
        duration_ms <= max_duration_ms
    ), f"{operation} took {duration_ms:.2f}ms, should be <= {max_duration_ms}ms"


async def wait_for_condition(
    condition_func: Any, timeout_seconds: float = 5.0, check_interval: float = 0.1
) -> bool:
    """Wait for condition to be true with timeout."""
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        if condition_func():
            return True
        await asyncio.sleep(check_interval)
    return False


# Integration test helpers
class IntegrationTestEnvironment:
    """Helper for managing integration test environment."""

    def __init__(self) -> None:
        self.test_index_created = False
        self.test_data_loaded = False

    async def setup_test_environment(self) -> None:
        """Setup integration test environment."""
        # This would set up real test indices, databases, etc. for integration tests
        pass

    async def teardown_test_environment(self) -> None:
        """Teardown integration test environment."""
        # This would clean up test resources
        pass

    def is_integration_environment_available(self) -> bool:
        """Check if integration test environment is available."""
        # Check for required environment variables, services, etc.
        return (
            os.getenv("TEST_PINECONE_API_KEY") is not None
            and os.getenv("TEST_REDIS_URL") is not None
        )


@pytest.fixture(scope="session")
def integration_env() -> IntegrationTestEnvironment:
    """Integration test environment fixture."""
    return IntegrationTestEnvironment()


# Markers for different test types
pytestmark = [
    pytest.mark.asyncio,
]
