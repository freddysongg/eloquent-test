"""
RAG (Retrieval-Augmented Generation) service for document retrieval.

Implements complete RAG pipeline with Pinecone vector search,
embedding generation, and context optimization for AI responses.
"""

import logging
from typing import Any, Dict, List, Optional

from app.integrations.pinecone_client import PineconeClient
from app.integrations.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class RAGService:
    """Service for RAG pipeline operations with Pinecone and context management."""
    
    def __init__(self) -> None:
        """Initialize RAG service with Pinecone client."""
        self.pinecone_client = PineconeClient()
        logger.info("RAG service initialized with Pinecone client")
    
    async def retrieve_context(
        self,
        query: str,
        top_k: int = 5,
        correlation_id: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context documents from Pinecone.
        
        Args:
            query: User query for semantic search
            top_k: Number of documents to retrieve
            correlation_id: Request correlation ID
        
        Returns:
            List of relevant document chunks with metadata
        """
        logger.info(
            f"Retrieving context for query",
            extra={
                "correlation_id": correlation_id,
                "query_length": len(query),
                "top_k": top_k
            }
        )
        
        try:
            # Check cache first
            redis_client = await get_redis_client()
            cache_key = f"rag_context:{hash(query)}:{top_k}"
            cached_results = await redis_client.get_json(cache_key, correlation_id)
            
            if cached_results:
                logger.info(
                    f"Retrieved context from cache",
                    extra={"correlation_id": correlation_id}
                )
                return cached_results
            
            # Generate query embedding
            query_embedding = await self.pinecone_client.embed_text(
                query, 
                correlation_id
            )
            
            # Search Pinecone for similar documents
            documents = await self.pinecone_client.search_documents(
                query_embedding=query_embedding,
                top_k=top_k,
                correlation_id=correlation_id
            )
            
            # Apply additional relevance scoring
            enhanced_documents = []
            for doc in documents:
                enhanced_score = self.pinecone_client.calculate_relevance_score(
                    doc["score"],
                    doc["metadata"]
                )
                
                enhanced_doc = {
                    **doc,
                    "enhanced_score": enhanced_score,
                    "relevance_tier": self._get_relevance_tier(enhanced_score)
                }
                
                enhanced_documents.append(enhanced_doc)
            
            # Sort by enhanced score
            enhanced_documents.sort(key=lambda x: x["enhanced_score"], reverse=True)
            
            # Cache results for 5 minutes
            await redis_client.set_json(
                cache_key, 
                enhanced_documents, 
                expiration=300,
                correlation_id=correlation_id
            )
            
            logger.info(
                f"Context retrieval completed",
                extra={
                    "correlation_id": correlation_id,
                    "documents_found": len(enhanced_documents),
                    "avg_score": sum(doc["enhanced_score"] for doc in enhanced_documents) / len(enhanced_documents) if enhanced_documents else 0
                }
            )
            
            return enhanced_documents
            
        except Exception as e:
            logger.error(
                f"Context retrieval failed: {str(e)}",
                extra={"correlation_id": correlation_id}
            )
            # Return empty list on failure rather than raising
            return []
    
    async def rerank_documents(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        correlation_id: str = ""
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
            extra={
                "correlation_id": correlation_id,
                "document_count": len(documents)
            }
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
                    "overlap_ratio": overlap_score
                }
                
                reranked_documents.append(reranked_doc)
            
            # Sort by rerank score
            reranked_documents.sort(key=lambda x: x["rerank_score"], reverse=True)
            
            logger.info(
                f"Document reranking completed",
                extra={
                    "correlation_id": correlation_id,
                    "avg_rerank_score": sum(doc["rerank_score"] for doc in reranked_documents) / len(reranked_documents) if reranked_documents else 0
                }
            )
            
            return reranked_documents
            
        except Exception as e:
            logger.error(
                f"Document reranking failed: {str(e)}",
                extra={"correlation_id": correlation_id}
            )
            # Return original documents on failure
            return documents
    
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
        max_length: int = 2000
    ) -> str:
        """
        Build context prompt from retrieved documents.
        
        Args:
            documents: Retrieved and ranked documents
            max_length: Maximum context length in characters
        
        Returns:
            Formatted context string for AI prompt
        """
        if not documents:
            return ""
        
        context_parts = []
        current_length = 0
        
        for i, doc in enumerate(documents):
            content = doc.get("content", "").strip()
            source = doc.get("source", "")
            category = doc.get("category", "")
            
            # Format document section
            doc_section = f"[Document {i+1}]"
            if category:
                doc_section += f" ({category})"
            doc_section += f"\n{content}\n"
            
            # Check if adding this document would exceed limit
            if current_length + len(doc_section) > max_length:
                break
            
            context_parts.append(doc_section)
            current_length += len(doc_section)
        
        context = "\n".join(context_parts)
        
        if context:
            context = f"Relevant information from knowledge base:\n\n{context}"
        
        return context