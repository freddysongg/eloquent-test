"""
Pinecone vector database client for RAG document retrieval.

Implements async client for Pinecone with embedding generation,
vector search, and relevance scoring for fintech FAQ documents.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx
from pinecone import Pinecone, ServerlessSpec

from app.core.config import settings
from app.core.exceptions import ExternalServiceException

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
            self.index = self.client.Index(
                name=self.index_name,
                host=self.index_host
            )
            
            logger.info(f"Pinecone client initialized for index: {self.index_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone client: {str(e)}")
            raise ExternalServiceException(
                "Pinecone",
                f"Client initialization failed: {str(e)}"
            )
    
    async def search_documents(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
        correlation_id: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents using vector similarity.
        
        Args:
            query_embedding: Query vector embedding (1024 dimensions)
            top_k: Number of similar documents to retrieve
            filter_metadata: Optional metadata filter for search
            correlation_id: Request correlation ID for tracking
        
        Returns:
            List of similar documents with metadata and scores
        
        Raises:
            ExternalServiceException: If Pinecone search fails
        """
        logger.info(
            f"Searching Pinecone index",
            extra={
                "correlation_id": correlation_id,
                "index_name": self.index_name,
                "top_k": top_k,
                "has_filter": bool(filter_metadata),
                "embedding_dims": len(query_embedding)
            }
        )
        
        try:
            # Perform vector search
            search_response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.index.query(
                    vector=query_embedding,
                    top_k=top_k,
                    filter=filter_metadata,
                    include_metadata=True,
                    include_values=False
                )
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
                f"Pinecone search completed",
                extra={
                    "correlation_id": correlation_id,
                    "results_count": len(documents),
                    "avg_score": sum(doc["score"] for doc in documents) / len(documents) if documents else 0,
                    "top_score": max(doc["score"] for doc in documents) if documents else 0
                }
            )
            
            return documents
            
        except Exception as e:
            logger.error(
                f"Pinecone search failed: {str(e)}",
                extra={"correlation_id": correlation_id}
            )
            raise ExternalServiceException(
                "Pinecone",
                f"Vector search failed: {str(e)}",
                correlation_id=correlation_id
            )
    
    async def embed_text(
        self,
        text: str,
        correlation_id: str = ""
    ) -> List[float]:
        """
        Generate embedding for text using llama-text-embed-v2 model.
        
        Args:
            text: Text to embed
            correlation_id: Request correlation ID for tracking
        
        Returns:
            Text embedding vector (1024 dimensions)
        
        Raises:
            ExternalServiceException: If embedding generation fails
        """
        logger.info(
            f"Generating text embedding",
            extra={
                "correlation_id": correlation_id,
                "text_length": len(text)
            }
        )
        
        try:
            # Use Pinecone's embedding service (or fallback to external service)
            # Note: This is a simplified implementation
            # In production, you would use the actual embedding model API
            
            # For now, use a placeholder embedding generation
            # TODO: Implement actual llama-text-embed-v2 API call
            
            # Simulate embedding API call
            embedding = await self._generate_embedding_via_api(text, correlation_id)
            
            logger.info(
                f"Text embedding generated",
                extra={
                    "correlation_id": correlation_id,
                    "embedding_dims": len(embedding)
                }
            )
            
            return embedding
            
        except Exception as e:
            logger.error(
                f"Text embedding failed: {str(e)}",
                extra={"correlation_id": correlation_id}
            )
            raise ExternalServiceException(
                "Pinecone",
                f"Text embedding failed: {str(e)}",
                correlation_id=correlation_id
            )
    
    async def _generate_embedding_via_api(
        self,
        text: str,
        correlation_id: str = ""
    ) -> List[float]:
        """
        Generate embedding using external embedding API.
        
        Args:
            text: Text to embed
            correlation_id: Request correlation ID
        
        Returns:
            Embedding vector
        """
        # Placeholder implementation
        # TODO: Implement actual embedding API call to llama-text-embed-v2
        
        # For demonstration, create a simple hash-based embedding
        import hashlib
        import numpy as np
        
        # Create deterministic "embedding" from text hash
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        # Convert to pseudo-embedding vector (1024 dimensions)
        np.random.seed(int(text_hash[:8], 16))
        embedding = np.random.normal(0, 1, 1024).tolist()
        
        # Normalize to unit vector
        magnitude = np.linalg.norm(embedding)
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]
        
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
            extra={
                "correlation_id": correlation_id,
                "index_name": self.index_name
            }
        )
        
        try:
            # Get index stats
            stats_response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.index.describe_index_stats()
            )
            
            stats = {
                "total_vector_count": stats_response.total_vector_count,
                "dimension": stats_response.dimension,
                "index_fullness": stats_response.index_fullness,
                "namespaces": {}
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
                    "fullness": stats["index_fullness"]
                }
            )
            
            return stats
            
        except Exception as e:
            logger.error(
                f"Failed to get Pinecone index stats: {str(e)}",
                extra={"correlation_id": correlation_id}
            )
            raise ExternalServiceException(
                "Pinecone",
                f"Failed to get index stats: {str(e)}",
                correlation_id=correlation_id
            )
    
    async def health_check(self) -> bool:
        """
        Check Pinecone index health.
        
        Returns:
            True if index is healthy, False otherwise
        """
        try:
            # Simple health check - get index stats
            stats = await self.get_index_stats()
            return stats["total_vector_count"] > 0
            
        except Exception as e:
            logger.error(f"Pinecone health check failed: {str(e)}")
            return False
    
    def calculate_relevance_score(
        self,
        similarity_score: float,
        metadata: Dict[str, Any]
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
            "general": 0.9
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