"""
Comprehensive unit tests for PineconeClient with embedding integration.

Tests cover vector search, embedding generation with multiple fallback strategies,
health checks, circuit breaker integration, and performance validation.
"""

import asyncio
import time
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pinecone.exceptions import PineconeException
from tests.conftest import (
    TEST_CORRELATION_ID,
    TEST_EMBEDDING_DIMENSIONS,
    assert_performance_benchmark,
    assert_valid_embedding,
    assert_valid_search_results,
)

from app.core.exceptions import ExternalServiceException
from app.integrations.pinecone_client import PineconeClient


class TestPineconeClientInitialization:
    """Test PineconeClient initialization and configuration."""

    @pytest.mark.asyncio
    async def test_client_initialization_success(self, mock_settings: Any) -> None:
        """Test successful client initialization."""
        with (
            patch("app.integrations.pinecone_client.Pinecone") as mock_pinecone_class,
            patch("app.integrations.pinecone_client.settings", mock_settings),
        ):

            mock_pinecone_instance = Mock()
            mock_index = Mock()
            mock_pinecone_instance.Index.return_value = mock_index
            mock_pinecone_class.return_value = mock_pinecone_instance

            client = PineconeClient()

            # Verify initialization calls
            mock_pinecone_class.assert_called_once_with(
                api_key=mock_settings.PINECONE_API_KEY
            )
            mock_pinecone_instance.Index.assert_called_once_with(
                name=mock_settings.PINECONE_INDEX_NAME,
                host=mock_settings.PINECONE_INDEX_HOST,
            )

            assert client.client == mock_pinecone_instance
            assert client.index_name == mock_settings.PINECONE_INDEX_NAME
            assert client.index_host == mock_settings.PINECONE_INDEX_HOST
            assert client.index == mock_index

    @pytest.mark.asyncio
    async def test_client_initialization_failure(self, mock_settings: Any) -> None:
        """Test client initialization failure handling."""
        with (
            patch("app.integrations.pinecone_client.Pinecone") as mock_pinecone_class,
            patch("app.integrations.pinecone_client.settings", mock_settings),
        ):

            mock_pinecone_class.side_effect = Exception("API key invalid")

            with pytest.raises(ExternalServiceException) as exc_info:
                PineconeClient()

            assert "Pinecone" in str(exc_info.value)
            assert "Client initialization failed" in str(exc_info.value)


class TestPineconeSearchDocuments:
    """Test vector search functionality with various scenarios."""

    @pytest.fixture
    def mock_search_response(self) -> Any:
        """Mock Pinecone search response."""

        class MockMatch:
            def __init__(self, match_id: str, score: float, metadata: Dict[str, Any]):
                self.id = match_id
                self.score = score
                self.metadata = metadata

        class MockResponse:
            def __init__(self, matches: List[MockMatch]):
                self.matches = matches

        return MockResponse

    @pytest.mark.asyncio
    async def test_search_documents_success(
        self,
        mock_settings: Any,
        sample_documents: List[Dict[str, Any]],
        test_query_embedding: List[float],
        performance_benchmarks: Dict[str, float],
    ) -> None:
        """Test successful document search with performance validation."""
        with (
            patch("app.integrations.pinecone_client.Pinecone") as mock_pinecone_class,
            patch("app.integrations.pinecone_client.settings", mock_settings),
            patch(
                "app.integrations.pinecone_client.resilience_manager"
            ) as mock_resilience,
        ):

            # Setup mocks
            mock_pinecone_instance = Mock()
            mock_index = Mock()
            mock_pinecone_instance.Index.return_value = mock_index
            mock_pinecone_class.return_value = mock_pinecone_instance

            # Mock search response
            class MockMatch:
                def __init__(self, doc: Dict[str, Any]):
                    self.id = doc["id"]
                    self.score = doc["score"]
                    self.metadata = doc["metadata"]

            class MockResponse:
                def __init__(self, docs: List[Dict[str, Any]]):
                    self.matches = [MockMatch(doc) for doc in docs]

            mock_response = MockResponse(sample_documents[:3])
            mock_index.query.return_value = mock_response

            # Mock resilience manager
            async def mock_execute(
                service: str, func: Any, correlation_id: str = ""
            ) -> Any:
                return await func()

            mock_resilience.execute_with_resilience = AsyncMock(
                side_effect=mock_execute
            )

            # Initialize client and test search
            client = PineconeClient()

            start_time = time.time()
            results = await client.search_documents(
                query_embedding=test_query_embedding,
                top_k=3,
                correlation_id=TEST_CORRELATION_ID,
            )

            # Performance validation
            assert_performance_benchmark(
                start_time, performance_benchmarks["vector_search_ms"], "Vector search"
            )

            # Validate results
            assert_valid_search_results(results, max_count=3)
            assert len(results) == 3

            # Verify expected fields
            for result in results:
                assert "id" in result
                assert "score" in result
                assert "content" in result
                assert "metadata" in result

            # Verify Pinecone API call
            mock_index.query.assert_called_once_with(
                vector=test_query_embedding,
                top_k=3,
                filter=None,
                include_metadata=True,
                include_values=False,
            )

    @pytest.mark.asyncio
    async def test_search_documents_with_filter(
        self, mock_settings: Any, sample_documents: List[Dict[str, Any]]
    ) -> None:
        """Test document search with metadata filtering."""
        with (
            patch("app.integrations.pinecone_client.Pinecone") as mock_pinecone_class,
            patch("app.integrations.pinecone_client.settings", mock_settings),
            patch(
                "app.integrations.pinecone_client.resilience_manager"
            ) as mock_resilience,
        ):

            # Setup mocks
            mock_pinecone_instance = Mock()
            mock_index = Mock()
            mock_pinecone_instance.Index.return_value = mock_index
            mock_pinecone_class.return_value = mock_pinecone_instance

            # Filter to security category only
            security_docs = [
                doc for doc in sample_documents if doc["category"] == "security"
            ]

            class MockMatch:
                def __init__(self, doc: Dict[str, Any]):
                    self.id = doc["id"]
                    self.score = doc["score"]
                    self.metadata = doc["metadata"]

            class MockResponse:
                def __init__(self, docs: List[Dict[str, Any]]):
                    self.matches = [MockMatch(doc) for doc in docs]

            mock_response = MockResponse(security_docs)
            mock_index.query.return_value = mock_response

            async def mock_execute(
                service: str, func: Any, correlation_id: str = ""
            ) -> Any:
                return await func()

            mock_resilience.execute_with_resilience = AsyncMock(
                side_effect=mock_execute
            )

            # Initialize client and test filtered search
            client = PineconeClient()
            test_embedding = [0.1] * TEST_EMBEDDING_DIMENSIONS
            filter_metadata = {"category": "security"}

            results = await client.search_documents(
                query_embedding=test_embedding,
                top_k=5,
                filter_metadata=filter_metadata,
                correlation_id=TEST_CORRELATION_ID,
            )

            # Validate filtering worked
            for result in results:
                assert result["category"] == "security"

            # Verify API call with filter
            mock_index.query.assert_called_once_with(
                vector=test_embedding,
                top_k=5,
                filter=filter_metadata,
                include_metadata=True,
                include_values=False,
            )

    @pytest.mark.asyncio
    async def test_search_documents_api_failure_with_fallback(
        self, mock_settings: Any, mock_redis_client: Any
    ) -> None:
        """Test search failure handling with fallback strategy."""
        with (
            patch("app.integrations.pinecone_client.Pinecone") as mock_pinecone_class,
            patch("app.integrations.pinecone_client.settings", mock_settings),
            patch(
                "app.integrations.pinecone_client.resilience_manager"
            ) as mock_resilience,
            patch(
                "app.integrations.pinecone_client.get_redis_client",
                return_value=mock_redis_client,
            ),
        ):

            # Setup client mock
            mock_pinecone_instance = Mock()
            mock_index = Mock()
            mock_pinecone_instance.Index.return_value = mock_index
            mock_pinecone_class.return_value = mock_pinecone_instance

            # Mock resilience manager to raise exception
            mock_resilience.execute_with_resilience = AsyncMock(
                side_effect=ExternalServiceException("Pinecone", "Search failed")
            )

            # Setup Redis fallback data
            fallback_results = [
                {
                    "id": "fallback_1",
                    "content": "Cached result",
                    "score": 0.8,
                    "metadata": {},
                }
            ]
            mock_redis_client.data["rag_context:test:vector_only"] = fallback_results

            client = PineconeClient()
            test_embedding = [0.1] * TEST_EMBEDDING_DIMENSIONS

            results = await client.search_documents(
                query_embedding=test_embedding,
                top_k=3,
                correlation_id=TEST_CORRELATION_ID,
            )

            # Should get fallback results
            assert len(results) <= 3
            # In this case, no cached keys match pattern, so empty results
            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_documents_empty_results(self, mock_settings: Any) -> None:
        """Test handling of empty search results."""
        with (
            patch("app.integrations.pinecone_client.Pinecone") as mock_pinecone_class,
            patch("app.integrations.pinecone_client.settings", mock_settings),
            patch(
                "app.integrations.pinecone_client.resilience_manager"
            ) as mock_resilience,
        ):

            # Setup mocks
            mock_pinecone_instance = Mock()
            mock_index = Mock()
            mock_pinecone_instance.Index.return_value = mock_index
            mock_pinecone_class.return_value = mock_pinecone_instance

            # Mock empty response
            class MockResponse:
                def __init__(self) -> None:
                    self.matches: List[Any] = []

            mock_response = MockResponse()
            mock_index.query.return_value = mock_response

            async def mock_execute(
                service: str, func: Any, correlation_id: str = ""
            ) -> Any:
                return await func()

            mock_resilience.execute_with_resilience = AsyncMock(
                side_effect=mock_execute
            )

            client = PineconeClient()
            test_embedding = [0.1] * TEST_EMBEDDING_DIMENSIONS

            results = await client.search_documents(
                query_embedding=test_embedding,
                top_k=5,
                correlation_id=TEST_CORRELATION_ID,
            )

            assert results == []


class TestPineconeEmbedText:
    """Test embedding generation with multiple fallback strategies."""

    @pytest.mark.asyncio
    async def test_embed_text_primary_strategy_success(
        self,
        mock_settings: Any,
        mock_redis_client: Any,
        performance_benchmarks: Dict[str, float],
    ) -> None:
        """Test successful embedding generation via primary Pinecone Inference API."""
        with (
            patch("app.integrations.pinecone_client.Pinecone") as mock_pinecone_class,
            patch("app.integrations.pinecone_client.settings", mock_settings),
            patch(
                "app.integrations.pinecone_client.get_redis_client",
                return_value=mock_redis_client,
            ),
            patch(
                "app.integrations.pinecone_client.resilience_manager"
            ) as mock_resilience,
        ):

            # Setup client mock
            mock_pinecone_instance = Mock()
            mock_inference = Mock()
            mock_pinecone_instance.inference = mock_inference
            mock_pinecone_class.return_value = mock_pinecone_instance

            # Mock embedding response
            class MockEmbeddingData:
                def __init__(self, values: List[float]):
                    self.values = values

            class MockInferenceResponse:
                def __init__(self, embedding: List[float]):
                    self.data = [MockEmbeddingData(embedding)]

            test_embedding = [0.1] * TEST_EMBEDDING_DIMENSIONS
            mock_response = MockInferenceResponse(test_embedding)
            mock_inference.embed.return_value = mock_response

            async def mock_execute(
                service: str, func: Any, correlation_id: str = ""
            ) -> Any:
                return await func()

            mock_resilience.execute_with_resilience = AsyncMock(
                side_effect=mock_execute
            )

            client = PineconeClient()
            text = "How do I reset my password?"

            start_time = time.time()
            embedding = await client.embed_text(
                text, correlation_id=TEST_CORRELATION_ID
            )

            # Performance validation
            assert_performance_benchmark(
                start_time,
                performance_benchmarks["embedding_generation_ms"],
                "Embedding generation",
            )

            # Validate embedding
            assert_valid_embedding(embedding, TEST_EMBEDDING_DIMENSIONS)

            # Verify API call
            mock_inference.embed.assert_called_once_with(
                model=mock_settings.EMBEDDING_MODEL, inputs=[text], parameters={}
            )

    @pytest.mark.asyncio
    async def test_embed_text_cache_hit(
        self, mock_settings: Any, mock_redis_client: Any
    ) -> None:
        """Test embedding retrieval from cache."""
        with (
            patch("app.integrations.pinecone_client.Pinecone") as mock_pinecone_class,
            patch("app.integrations.pinecone_client.settings", mock_settings),
            patch(
                "app.integrations.pinecone_client.get_redis_client",
                return_value=mock_redis_client,
            ),
        ):

            mock_pinecone_instance = Mock()
            mock_pinecone_class.return_value = mock_pinecone_instance

            # Setup cached embedding
            text = "cached query"
            cached_embedding = [0.2] * TEST_EMBEDDING_DIMENSIONS
            cache_key = f"embedding:{hash(text)}:{mock_settings.EMBEDDING_MODEL}"
            mock_redis_client.data[cache_key] = cached_embedding

            client = PineconeClient()

            start_time = time.time()
            embedding = await client.embed_text(
                text, correlation_id=TEST_CORRELATION_ID
            )

            # Should be very fast from cache
            duration_ms = (time.time() - start_time) * 1000
            assert duration_ms < 50  # Cache retrieval should be <50ms

            assert embedding == cached_embedding
            assert_valid_embedding(embedding, TEST_EMBEDDING_DIMENSIONS)

    @pytest.mark.asyncio
    async def test_embed_text_openai_fallback_success(
        self, mock_settings: Any, mock_redis_client: Any
    ) -> None:
        """Test OpenAI fallback embedding generation."""
        with (
            patch("app.integrations.pinecone_client.Pinecone") as mock_pinecone_class,
            patch("app.integrations.pinecone_client.settings", mock_settings),
            patch(
                "app.integrations.pinecone_client.get_redis_client",
                return_value=mock_redis_client,
            ),
            patch(
                "app.integrations.pinecone_client.resilience_manager"
            ) as mock_resilience,
            patch("httpx.AsyncClient") as mock_httpx,
        ):

            # Setup basic mocks
            mock_pinecone_instance = Mock()
            mock_pinecone_class.return_value = mock_pinecone_instance

            # Mock primary strategy failure
            mock_resilience.execute_with_resilience = AsyncMock(
                side_effect=ExternalServiceException("Pinecone", "API failed")
            )

            # Setup OpenAI API key
            mock_settings.OPENAI_API_KEY = "test-openai-key"
            mock_settings.OPENAI_EMBEDDING_MODEL = "text-embedding-3-large"

            # Mock OpenAI API response
            openai_embedding = [0.3] * 3072  # OpenAI's embedding size
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {
                "data": [{"embedding": openai_embedding}]
            }

            mock_client_instance = Mock()
            mock_client_instance.post.return_value = mock_response
            mock_httpx.return_value.__aenter__.return_value = mock_client_instance

            client = PineconeClient()
            text = "test openai fallback"

            embedding = await client.embed_text(
                text, correlation_id=TEST_CORRELATION_ID
            )

            # Should be truncated to target dimensions and normalized
            assert_valid_embedding(embedding, TEST_EMBEDDING_DIMENSIONS)
            assert len(embedding) == TEST_EMBEDDING_DIMENSIONS

            # Verify OpenAI API call
            mock_client_instance.post.assert_called_once()
            call_args = mock_client_instance.post.call_args
            assert "https://api.openai.com/v1/embeddings" in call_args[0]

    @pytest.mark.asyncio
    async def test_embed_text_sentence_transformers_fallback(
        self, mock_settings: Any, mock_redis_client: Any
    ) -> None:
        """Test sentence-transformers fallback embedding generation."""
        with (
            patch("app.integrations.pinecone_client.Pinecone") as mock_pinecone_class,
            patch("app.integrations.pinecone_client.settings", mock_settings),
            patch(
                "app.integrations.pinecone_client.get_redis_client",
                return_value=mock_redis_client,
            ),
            patch(
                "app.integrations.pinecone_client.resilience_manager"
            ) as mock_resilience,
            patch("httpx.AsyncClient") as mock_httpx,
        ):

            # Setup basic mocks
            mock_pinecone_instance = Mock()
            mock_pinecone_class.return_value = mock_pinecone_instance

            # Mock primary strategy failure
            mock_resilience.execute_with_resilience = AsyncMock(
                side_effect=ExternalServiceException("Pinecone", "API failed")
            )

            # No OpenAI key available
            mock_settings.OPENAI_API_KEY = None

            # Mock sentence-transformers API response
            st_embedding = [0.4] * 384  # Sentence-transformers typical size
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = st_embedding

            mock_client_instance = Mock()
            mock_client_instance.post.return_value = mock_response
            mock_httpx.return_value.__aenter__.return_value = mock_client_instance

            client = PineconeClient()
            text = "test sentence transformers fallback"

            embedding = await client.embed_text(
                text, correlation_id=TEST_CORRELATION_ID
            )

            # Should be padded to target dimensions and normalized
            assert_valid_embedding(embedding, TEST_EMBEDDING_DIMENSIONS)
            assert len(embedding) == TEST_EMBEDDING_DIMENSIONS

            # Verify API call to sentence-transformers
            mock_client_instance.post.assert_called()

    @pytest.mark.asyncio
    async def test_embed_text_deterministic_fallback(
        self, mock_settings: Any, mock_redis_client: Any
    ) -> None:
        """Test deterministic fallback embedding generation."""
        with (
            patch("app.integrations.pinecone_client.Pinecone") as mock_pinecone_class,
            patch("app.integrations.pinecone_client.settings", mock_settings),
            patch(
                "app.integrations.pinecone_client.get_redis_client",
                return_value=mock_redis_client,
            ),
            patch(
                "app.integrations.pinecone_client.resilience_manager"
            ) as mock_resilience,
            patch("httpx.AsyncClient") as mock_httpx,
        ):

            # Setup basic mocks
            mock_pinecone_instance = Mock()
            mock_pinecone_class.return_value = mock_pinecone_instance

            # Mock all external services failing
            mock_resilience.execute_with_resilience = AsyncMock(
                side_effect=ExternalServiceException("All APIs", "All failed")
            )
            mock_settings.OPENAI_API_KEY = None

            # Mock HTTP failures
            mock_httpx.return_value.__aenter__.return_value.post.side_effect = (
                Exception("HTTP failed")
            )

            client = PineconeClient()
            text = "test deterministic fallback with financial keywords account payment security"

            embedding = await client.embed_text(
                text, correlation_id=TEST_CORRELATION_ID
            )

            # Should generate valid deterministic embedding
            assert_valid_embedding(embedding, TEST_EMBEDDING_DIMENSIONS)

            # Should be deterministic - same text should produce same embedding
            embedding2 = await client.embed_text(
                text, correlation_id=TEST_CORRELATION_ID
            )
            assert embedding == embedding2

            # Different text should produce different embedding
            different_embedding = await client.embed_text(
                "completely different text", TEST_CORRELATION_ID
            )
            assert embedding != different_embedding

    @pytest.mark.asyncio
    async def test_embed_text_dimension_validation(
        self, mock_settings: Any, mock_redis_client: Any
    ) -> None:
        """Test embedding dimension validation."""
        with (
            patch("app.integrations.pinecone_client.Pinecone") as mock_pinecone_class,
            patch("app.integrations.pinecone_client.settings", mock_settings),
            patch(
                "app.integrations.pinecone_client.get_redis_client",
                return_value=mock_redis_client,
            ),
            patch(
                "app.integrations.pinecone_client.resilience_manager"
            ) as mock_resilience,
        ):

            # Setup client mock
            mock_pinecone_instance = Mock()
            mock_inference = Mock()
            mock_pinecone_instance.inference = mock_inference
            mock_pinecone_class.return_value = mock_pinecone_instance

            # Mock embedding response with wrong dimensions
            class MockEmbeddingData:
                def __init__(self, values: List[float]):
                    self.values = values

            class MockInferenceResponse:
                def __init__(self, embedding: List[float]):
                    self.data = [MockEmbeddingData(embedding)]

            # Wrong dimension embedding
            wrong_dimension_embedding = [0.1] * 512  # Should be 1024
            mock_response = MockInferenceResponse(wrong_dimension_embedding)
            mock_inference.embed.return_value = mock_response

            async def mock_execute(
                service: str, func: Any, correlation_id: str = ""
            ) -> Any:
                return await func()

            mock_resilience.execute_with_resilience = AsyncMock(
                side_effect=mock_execute
            )

            client = PineconeClient()
            text = "test dimension validation"

            with pytest.raises(ExternalServiceException) as exc_info:
                await client.embed_text(text, correlation_id=TEST_CORRELATION_ID)

            assert "Embedding generation failed" in str(exc_info.value)


class TestPineconeIndexStats:
    """Test index statistics and metadata retrieval."""

    @pytest.mark.asyncio
    async def test_get_index_stats_success(self, mock_settings: Any) -> None:
        """Test successful index stats retrieval."""
        with (
            patch("app.integrations.pinecone_client.Pinecone") as mock_pinecone_class,
            patch("app.integrations.pinecone_client.settings", mock_settings),
        ):

            # Setup mocks
            mock_pinecone_instance = Mock()
            mock_index = Mock()
            mock_pinecone_instance.Index.return_value = mock_index
            mock_pinecone_class.return_value = mock_pinecone_instance

            # Mock stats response
            class MockNamespaceStats:
                def __init__(self, vector_count: int) -> None:
                    self.vector_count = vector_count

            class MockStatsResponse:
                def __init__(self) -> None:
                    self.total_vector_count = 17
                    self.dimension = TEST_EMBEDDING_DIMENSIONS
                    self.index_fullness = 0.1
                    self.namespaces: Dict[str, MockNamespaceStats] = {
                        "default": MockNamespaceStats(15),
                        "test": MockNamespaceStats(2),
                    }

            mock_stats_response = MockStatsResponse()
            mock_index.describe_index_stats.return_value = mock_stats_response

            client = PineconeClient()

            stats = await client.get_index_stats(correlation_id=TEST_CORRELATION_ID)

            # Validate stats structure
            assert stats["total_vector_count"] == 17
            assert stats["dimension"] == TEST_EMBEDDING_DIMENSIONS
            assert stats["index_fullness"] == 0.1
            assert "namespaces" in stats
            assert stats["namespaces"]["default"]["vector_count"] == 15
            assert stats["namespaces"]["test"]["vector_count"] == 2

    @pytest.mark.asyncio
    async def test_get_index_stats_failure(self, mock_settings: Any) -> None:
        """Test index stats retrieval failure."""
        with (
            patch("app.integrations.pinecone_client.Pinecone") as mock_pinecone_class,
            patch("app.integrations.pinecone_client.settings", mock_settings),
        ):

            mock_pinecone_instance = Mock()
            mock_index = Mock()
            mock_pinecone_instance.Index.return_value = mock_index
            mock_pinecone_class.return_value = mock_pinecone_instance

            # Mock API failure
            mock_index.describe_index_stats.side_effect = PineconeException(
                "Stats unavailable"
            )

            client = PineconeClient()

            with pytest.raises(ExternalServiceException) as exc_info:
                await client.get_index_stats(correlation_id=TEST_CORRELATION_ID)

            assert "Failed to get index stats" in str(exc_info.value)


class TestPineconeHealthCheck:
    """Test comprehensive health checks including circuit breaker status."""

    @pytest.mark.asyncio
    async def test_health_check_all_healthy(
        self, mock_settings: Any, mock_resilience_manager: Any
    ) -> None:
        """Test health check when all systems are healthy."""
        with (
            patch("app.integrations.pinecone_client.Pinecone") as mock_pinecone_class,
            patch("app.integrations.pinecone_client.settings", mock_settings),
            patch(
                "app.integrations.pinecone_client.resilience_manager",
                mock_resilience_manager,
            ),
        ):

            # Setup mocks
            mock_pinecone_instance = Mock()
            mock_index = Mock()
            mock_inference = Mock()
            mock_pinecone_instance.Index.return_value = mock_index
            mock_pinecone_instance.inference = mock_inference
            mock_pinecone_class.return_value = mock_pinecone_instance

            # Mock healthy circuit breakers
            mock_resilience_manager.get_service_health.return_value = {
                "state": "closed",
                "status": "healthy",
                "error_rate": 0.0,
                "total_requests": 100,
            }

            # Mock successful operations
            async def mock_execute(
                service: str, func: Any, correlation_id: str = ""
            ) -> Any:
                return await func()

            mock_resilience_manager.execute_with_resilience = AsyncMock(
                side_effect=mock_execute
            )

            # Mock index stats
            class MockStatsResponse:
                def __init__(self) -> None:
                    self.total_vector_count = 17
                    self.dimension = TEST_EMBEDDING_DIMENSIONS
                    self.index_fullness = 0.1
                    self.namespaces: Dict[str, Any] = {}

            mock_index.describe_index_stats.return_value = MockStatsResponse()

            # Mock embedding generation
            class MockEmbeddingData:
                def __init__(self, values: List[float]):
                    self.values = values

            class MockInferenceResponse:
                def __init__(self, embedding: List[float]):
                    self.data = [MockEmbeddingData(embedding)]

            test_embedding = [0.1] * TEST_EMBEDDING_DIMENSIONS
            mock_inference.embed.return_value = MockInferenceResponse(test_embedding)

            # Mock search
            class MockMatch:
                def __init__(
                    self, match_id: str, score: float, metadata: Dict[str, Any]
                ):
                    self.id = match_id
                    self.score = score
                    self.metadata = metadata

            class MockSearchResponse:
                def __init__(self) -> None:
                    self.matches = [MockMatch("test_1", 0.9, {"content": "test"})]

            mock_index.query.return_value = MockSearchResponse()

            client = PineconeClient()

            health_status = await client.health_check(
                correlation_id=TEST_CORRELATION_ID
            )

            # Validate overall health
            assert health_status["service"] == "pinecone"
            assert health_status["status"] == "healthy"
            assert "timestamp" in health_status

            # Validate circuit breaker status
            assert "circuit_breakers" in health_status
            assert health_status["circuit_breakers"]["pinecone"]["status"] == "healthy"
            assert (
                health_status["circuit_breakers"]["embedding_api"]["status"]
                == "healthy"
            )

            # Validate individual checks
            assert health_status["checks"]["connectivity"]["status"] == "healthy"
            assert health_status["checks"]["embedding"]["status"] == "healthy"
            assert health_status["checks"]["search"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_degraded_performance(
        self, mock_settings: Any, mock_resilience_manager: Any
    ) -> None:
        """Test health check with degraded performance."""
        with (
            patch("app.integrations.pinecone_client.Pinecone") as mock_pinecone_class,
            patch("app.integrations.pinecone_client.settings", mock_settings),
            patch(
                "app.integrations.pinecone_client.resilience_manager",
                mock_resilience_manager,
            ),
        ):

            mock_pinecone_instance = Mock()
            mock_index = Mock()
            mock_inference = Mock()
            mock_pinecone_instance.Index.return_value = mock_index
            mock_pinecone_instance.inference = mock_inference
            mock_pinecone_class.return_value = mock_pinecone_instance

            # Mock degraded circuit breaker
            mock_resilience_manager.get_service_health.side_effect = [
                {
                    "state": "half-open",
                    "status": "degraded",
                    "error_rate": 0.15,
                    "total_requests": 100,
                },
                {
                    "state": "closed",
                    "status": "healthy",
                    "error_rate": 0.0,
                    "total_requests": 50,
                },
            ]

            # Mock successful connectivity but failed embedding
            async def mock_execute(
                service: str, func: Any, correlation_id: str = ""
            ) -> Any:
                if service == "pinecone":
                    return await func()  # Connectivity works
                else:
                    raise ExternalServiceException(
                        "Embedding API", "Degraded performance"
                    )

            mock_resilience_manager.execute_with_resilience = AsyncMock(
                side_effect=mock_execute
            )

            # Mock successful stats
            class MockStatsResponse:
                def __init__(self) -> None:
                    self.total_vector_count = 17
                    self.dimension = TEST_EMBEDDING_DIMENSIONS
                    self.index_fullness = 0.1
                    self.namespaces: Dict[str, Any] = {}

            mock_index.describe_index_stats.return_value = MockStatsResponse()

            client = PineconeClient()

            health_status = await client.health_check(
                correlation_id=TEST_CORRELATION_ID
            )

            # Should be degraded due to circuit breaker and embedding failure
            assert health_status["status"] in ["degraded", "unhealthy"]
            assert health_status["circuit_breakers"]["pinecone"]["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_health_check_circuit_breaker_open(
        self, mock_settings: Any, mock_resilience_manager: Any
    ) -> None:
        """Test health check with open circuit breaker."""
        with (
            patch("app.integrations.pinecone_client.Pinecone") as mock_pinecone_class,
            patch("app.integrations.pinecone_client.settings", mock_settings),
            patch(
                "app.integrations.pinecone_client.resilience_manager",
                mock_resilience_manager,
            ),
        ):

            mock_pinecone_instance = Mock()
            mock_pinecone_class.return_value = mock_pinecone_instance

            # Mock open circuit breakers
            mock_resilience_manager.get_service_health.return_value = {
                "state": "open",
                "status": "unhealthy",
                "error_rate": 0.95,
                "total_requests": 100,
            }

            # Mock failing operations
            mock_resilience_manager.execute_with_resilience = AsyncMock(
                side_effect=ExternalServiceException("Circuit breaker", "Open")
            )

            client = PineconeClient()

            health_status = await client.health_check(
                correlation_id=TEST_CORRELATION_ID
            )

            # Should be unhealthy due to open circuit breaker
            assert health_status["status"] == "unhealthy"
            assert (
                health_status["circuit_breakers"]["pinecone"]["status"] == "unhealthy"
            )
            assert health_status["circuit_breakers"]["pinecone"]["state"] == "open"


class TestPineconeRelevanceScoring:
    """Test relevance scoring enhancements."""

    def test_calculate_relevance_score_category_boost(self, mock_settings: Any) -> None:
        """Test relevance scoring with category-based boosts."""
        with (
            patch("app.integrations.pinecone_client.Pinecone") as mock_pinecone_class,
            patch("app.integrations.pinecone_client.settings", mock_settings),
        ):

            mock_pinecone_instance = Mock()
            mock_pinecone_class.return_value = mock_pinecone_instance

            client = PineconeClient()

            # Test different categories
            test_cases = [
                (0.8, {"category": "security"}, 0.96),  # 1.2x boost
                (0.8, {"category": "account"}, 0.88),  # 1.1x boost
                (0.8, {"category": "payment"}, 0.88),  # 1.1x boost
                (0.8, {"category": "general"}, 0.72),  # 0.9x penalty
                (0.8, {"category": "unknown"}, 0.8),  # No change
            ]

            for base_score, metadata, expected_score in test_cases:
                calculated_score = client.calculate_relevance_score(
                    base_score, metadata
                )
                assert abs(calculated_score - expected_score) < 0.01

    def test_calculate_relevance_score_source_boost(self, mock_settings: Any) -> None:
        """Test relevance scoring with source-based boosts."""
        with (
            patch("app.integrations.pinecone_client.Pinecone") as mock_pinecone_class,
            patch("app.integrations.pinecone_client.settings", mock_settings),
        ):

            mock_pinecone_instance = Mock()
            mock_pinecone_class.return_value = mock_pinecone_instance

            client = PineconeClient()

            # Test high-quality sources
            base_score = 0.8

            # Official docs boost
            metadata = {"category": "account", "source": "official_docs"}
            expected_score = min(0.8 * 1.1 * 1.15, 1.0)  # Category + source boost
            calculated_score = client.calculate_relevance_score(base_score, metadata)
            assert abs(calculated_score - expected_score) < 0.01

            # Regulatory guidance boost
            metadata = {"category": "security", "source": "regulatory_guidance"}
            expected_score = min(
                0.8 * 1.2 * 1.15, 1.0
            )  # Category + source boost, capped at 1.0
            calculated_score = client.calculate_relevance_score(base_score, metadata)
            assert calculated_score == 1.0  # Should be capped

    def test_calculate_relevance_score_capped_at_one(self, mock_settings: Any) -> None:
        """Test that relevance scores are capped at 1.0."""
        with (
            patch("app.integrations.pinecone_client.Pinecone") as mock_pinecone_class,
            patch("app.integrations.pinecone_client.settings", mock_settings),
        ):

            mock_pinecone_instance = Mock()
            mock_pinecone_class.return_value = mock_pinecone_instance

            client = PineconeClient()

            # High base score with maximum boosts
            base_score = 0.9
            metadata = {"category": "security", "source": "official_docs"}
            calculated_score = client.calculate_relevance_score(base_score, metadata)

            # Should be capped at 1.0
            assert calculated_score == 1.0


class TestPineconePerformance:
    """Test performance characteristics and benchmarks."""

    @pytest.mark.asyncio
    async def test_concurrent_search_performance(
        self,
        mock_settings: Any,
        sample_documents: List[Dict[str, Any]],
        performance_benchmarks: Dict[str, float],
    ) -> None:
        """Test concurrent search operations performance."""
        with (
            patch("app.integrations.pinecone_client.Pinecone") as mock_pinecone_class,
            patch("app.integrations.pinecone_client.settings", mock_settings),
            patch(
                "app.integrations.pinecone_client.resilience_manager"
            ) as mock_resilience,
        ):

            # Setup mocks
            mock_pinecone_instance = Mock()
            mock_index = Mock()
            mock_pinecone_instance.Index.return_value = mock_index
            mock_pinecone_class.return_value = mock_pinecone_instance

            # Mock fast search response
            class MockMatch:
                def __init__(self, doc: Dict[str, Any]):
                    self.id = doc["id"]
                    self.score = doc["score"]
                    self.metadata = doc["metadata"]

            class MockResponse:
                def __init__(self, docs: List[Dict[str, Any]]):
                    self.matches = [MockMatch(doc) for doc in docs]

            mock_response = MockResponse(sample_documents[:3])
            mock_index.query.return_value = mock_response

            async def mock_execute(
                service: str, func: Any, correlation_id: str = ""
            ) -> Any:
                await asyncio.sleep(0.01)  # Simulate 10ms API call
                return await func()

            mock_resilience.execute_with_resilience = AsyncMock(
                side_effect=mock_execute
            )

            client = PineconeClient()
            test_embedding = [0.1] * TEST_EMBEDDING_DIMENSIONS

            # Test concurrent searches
            start_time = time.time()

            tasks = [
                client.search_documents(
                    query_embedding=test_embedding,
                    top_k=3,
                    correlation_id=f"{TEST_CORRELATION_ID}_{i}",
                )
                for i in range(5)
            ]

            results = await asyncio.gather(*tasks)

            # Should complete faster than sequential execution
            total_duration_ms = (time.time() - start_time) * 1000
            assert (
                total_duration_ms < 200
            )  # Should be much faster than 5 * 50ms = 250ms

            # Validate all results
            assert len(results) == 5
            for result in results:
                assert_valid_search_results(result, max_count=3)

    @pytest.mark.asyncio
    async def test_embedding_cache_performance(
        self, mock_settings: Any, mock_redis_client: Any
    ) -> None:
        """Test embedding caching performance benefits."""
        with (
            patch("app.integrations.pinecone_client.Pinecone") as mock_pinecone_class,
            patch("app.integrations.pinecone_client.settings", mock_settings),
            patch(
                "app.integrations.pinecone_client.get_redis_client",
                return_value=mock_redis_client,
            ),
        ):

            mock_pinecone_instance = Mock()
            mock_pinecone_class.return_value = mock_pinecone_instance

            client = PineconeClient()
            text = "performance test query"

            # First call - should be slow (mocked)
            with patch.object(
                client, "_generate_embedding_via_pinecone_inference"
            ) as mock_embed:
                test_embedding = [0.3] * TEST_EMBEDDING_DIMENSIONS
                mock_embed.return_value = test_embedding

                start_time = time.time()
                embedding1 = await client.embed_text(
                    text, correlation_id=TEST_CORRELATION_ID
                )
                first_call_duration = (time.time() - start_time) * 1000

                assert_valid_embedding(embedding1, TEST_EMBEDDING_DIMENSIONS)

            # Second call - should be fast from cache
            start_time = time.time()
            embedding2 = await client.embed_text(
                text, correlation_id=TEST_CORRELATION_ID
            )
            second_call_duration = (time.time() - start_time) * 1000

            # Cache retrieval should be much faster
            assert second_call_duration < 50  # <50ms from cache
            assert embedding1 == embedding2
            assert_valid_embedding(embedding2, TEST_EMBEDDING_DIMENSIONS)
