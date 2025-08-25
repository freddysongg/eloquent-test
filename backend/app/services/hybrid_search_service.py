"""
Hybrid Search Service for combining semantic vector search with keyword search.

Implements BM25 algorithm for keyword relevance scoring and combines with
vector similarity scores using configurable weights for optimal retrieval.
"""

import logging
import math
import re
from collections import defaultdict
from typing import Any, Dict, List, Tuple

import tiktoken

logger = logging.getLogger(__name__)


class BM25Scorer:
    """BM25 (Best Matching 25) scoring algorithm for keyword relevance."""

    def __init__(self, k1: float = 1.2, b: float = 0.75) -> None:
        """
        Initialize BM25 scorer with standard parameters.

        Args:
            k1: Term frequency saturation parameter (1.2-2.0 typical)
            b: Length normalization parameter (0.75 typical)
        """
        self.k1 = k1
        self.b = b
        self.corpus_size = 0
        self.avg_doc_length = 0.0
        self.doc_frequencies: Dict[str, int] = defaultdict(int)
        self.doc_lengths: Dict[str, int] = {}
        self.documents: Dict[str, List[str]] = {}

    def fit(self, documents: List[Dict[str, Any]]) -> None:
        """
        Build BM25 index from document corpus.

        Args:
            documents: List of documents with 'id' and 'content' fields
        """
        self.corpus_size = len(documents)

        if self.corpus_size == 0:
            logger.warning("Empty document corpus provided to BM25 scorer")
            return

        # Tokenize all documents and build statistics
        total_length = 0

        for doc in documents:
            doc_id = doc.get("id", str(hash(doc.get("content", ""))))
            content = doc.get("content", "")

            tokens = self._tokenize(content)
            self.documents[doc_id] = tokens
            self.doc_lengths[doc_id] = len(tokens)
            total_length += len(tokens)

            # Count document frequency for each term
            unique_terms = set(tokens)
            for term in unique_terms:
                self.doc_frequencies[term] += 1

        # Calculate average document length
        self.avg_doc_length = (
            total_length / self.corpus_size if self.corpus_size > 0 else 0.0
        )

        logger.info(
            f"BM25 index built: {self.corpus_size} documents, "
            f"avg_length={self.avg_doc_length:.1f}, "
            f"unique_terms={len(self.doc_frequencies)}"
        )

    def score(self, query: str, document_id: str) -> float:
        """
        Calculate BM25 score for query against specific document.

        Args:
            query: Search query string
            document_id: ID of document to score

        Returns:
            BM25 relevance score
        """
        if document_id not in self.documents:
            return 0.0

        query_terms = self._tokenize(query)
        doc_terms = self.documents[document_id]
        doc_length = self.doc_lengths[document_id]

        score = 0.0

        for term in query_terms:
            if term not in self.doc_frequencies:
                continue

            # Term frequency in document
            tf = doc_terms.count(term)

            # Inverse document frequency
            df = self.doc_frequencies[term]
            idf = math.log((self.corpus_size - df + 0.5) / (df + 0.5))

            # BM25 formula
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (
                1 - self.b + self.b * (doc_length / self.avg_doc_length)
            )

            term_score = idf * (numerator / denominator)
            score += term_score

        return max(score, 0.0)  # Ensure non-negative score

    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        Search documents for query and return top-k matches.

        Args:
            query: Search query string
            top_k: Number of top matches to return

        Returns:
            List of (document_id, score) tuples sorted by score descending
        """
        scores = []

        for doc_id in self.documents:
            score = self.score(query, doc_id)
            if score > 0:
                scores.append((doc_id, score))

        # Sort by score descending and return top-k
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into lowercase terms.

        Args:
            text: Input text to tokenize

        Returns:
            List of lowercase tokens
        """
        if not text:
            return []

        # Simple tokenization: lowercase, remove punctuation, split on whitespace
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)
        tokens = text.split()

        # Remove very short tokens
        tokens = [token for token in tokens if len(token) >= 2]

        return tokens


class HybridSearchService:
    """Service for hybrid search combining vector similarity and keyword matching."""

    def __init__(
        self,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        diversity_threshold: float = 0.85,
        max_context_tokens: int = 8000,
    ) -> None:
        """
        Initialize hybrid search service.

        Args:
            vector_weight: Weight for vector similarity scores (0.0-1.0)
            keyword_weight: Weight for keyword BM25 scores (0.0-1.0)
            diversity_threshold: Minimum cosine similarity for diversity filtering
            max_context_tokens: Maximum tokens for context window
        """
        if abs(vector_weight + keyword_weight - 1.0) > 0.001:
            raise ValueError("Vector and keyword weights must sum to 1.0")

        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
        self.diversity_threshold = diversity_threshold
        self.max_context_tokens = max_context_tokens

        self.bm25_scorer = BM25Scorer()
        self.tokenizer = tiktoken.encoding_for_model(
            "gpt-3.5-turbo"
        )  # Claude-compatible

        logger.info(
            f"HybridSearchService initialized: vector_weight={vector_weight}, "
            f"keyword_weight={keyword_weight}, diversity_threshold={diversity_threshold}"
        )

    def build_index(self, documents: List[Dict[str, Any]]) -> None:
        """
        Build BM25 index from document corpus.

        Args:
            documents: List of documents for indexing
        """
        self.bm25_scorer.fit(documents)
        logger.info(f"Hybrid search index built with {len(documents)} documents")

    def search(
        self,
        query: str,
        vector_results: List[Dict[str, Any]],
        top_k: int = 5,
        correlation_id: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining vector and keyword results.

        Args:
            query: Search query string
            vector_results: Results from vector similarity search
            top_k: Number of results to return
            correlation_id: Request correlation ID

        Returns:
            Hybrid search results with combined scores
        """
        logger.info(
            f"Performing hybrid search",
            extra={
                "correlation_id": correlation_id,
                "query_length": len(query),
                "vector_results": len(vector_results),
                "top_k": top_k,
            },
        )

        if not vector_results:
            logger.warning(
                f"No vector results provided for hybrid search",
                extra={"correlation_id": correlation_id},
            )
            return []

        # Get BM25 scores for all documents
        bm25_results = self.bm25_scorer.search(query, top_k=len(vector_results) * 2)
        bm25_scores = {doc_id: score for doc_id, score in bm25_results}

        # Normalize scores to [0, 1] range
        max_vector_score = max(
            (doc.get("score", 0) for doc in vector_results), default=1.0
        )
        max_bm25_score = max(bm25_scores.values()) if bm25_scores else 1.0

        # Combine vector and keyword scores
        hybrid_results = []

        for doc in vector_results:
            doc_id = doc.get("id", str(hash(doc.get("content", ""))))

            # Normalize individual scores
            vector_score = (
                doc.get("score", 0) / max_vector_score if max_vector_score > 0 else 0
            )
            bm25_score = (
                bm25_scores.get(doc_id, 0) / max_bm25_score if max_bm25_score > 0 else 0
            )

            # Calculate hybrid score
            hybrid_score = (
                self.vector_weight * vector_score + self.keyword_weight * bm25_score
            )

            # Calculate confidence score based on both signals
            confidence = self._calculate_confidence(
                vector_score, bm25_score, query, doc
            )

            # Create enhanced result
            hybrid_doc = {
                **doc,
                "hybrid_score": hybrid_score,
                "vector_score_normalized": vector_score,
                "bm25_score_normalized": bm25_score,
                "confidence": confidence,
                "source_attribution": self._get_source_attribution(doc),
            }

            hybrid_results.append(hybrid_doc)

        # Sort by hybrid score
        hybrid_results.sort(key=lambda x: x["hybrid_score"], reverse=True)

        # Apply diversity filtering
        diverse_results = self._apply_diversity_filter(hybrid_results, correlation_id)

        # Limit to top_k results
        final_results = diverse_results[:top_k]

        logger.info(
            f"Hybrid search completed",
            extra={
                "correlation_id": correlation_id,
                "results_before_diversity": len(hybrid_results),
                "results_after_diversity": len(diverse_results),
                "final_results": len(final_results),
                "avg_hybrid_score": (
                    sum(doc["hybrid_score"] for doc in final_results)
                    / len(final_results)
                    if final_results
                    else 0
                ),
                "avg_confidence": (
                    sum(doc["confidence"] for doc in final_results) / len(final_results)
                    if final_results
                    else 0
                ),
            },
        )

        return final_results

    def _calculate_confidence(
        self,
        vector_score: float,
        bm25_score: float,
        query: str,
        document: Dict[str, Any],
    ) -> float:
        """
        Calculate confidence score for search result.

        Args:
            vector_score: Normalized vector similarity score
            bm25_score: Normalized BM25 keyword score
            query: Original search query
            document: Document being scored

        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Base confidence from score alignment
        score_alignment = 1.0 - abs(vector_score - bm25_score)

        # Boost for high scores in both signals
        both_signals_high = min(vector_score, bm25_score) > 0.5
        signal_boost = 0.1 if both_signals_high else 0.0

        # Boost for exact query term matches in content
        content = document.get("content", "").lower()
        query_terms = set(query.lower().split())
        content_terms = set(content.split())
        exact_match_ratio = (
            len(query_terms.intersection(content_terms)) / len(query_terms)
            if query_terms
            else 0
        )
        exact_match_boost = exact_match_ratio * 0.2

        # Category relevance boost
        category_boost = (
            0.1
            if document.get("category") in ["account", "payment", "security"]
            else 0.0
        )

        confidence = min(
            score_alignment + signal_boost + exact_match_boost + category_boost, 1.0
        )

        return confidence

    def _get_source_attribution(self, document: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract source attribution information from document.

        Args:
            document: Document with metadata

        Returns:
            Source attribution dictionary
        """
        return {
            "source": document.get("source", "unknown"),
            "category": document.get("category", "general"),
            "title": document.get("title", ""),
            "id": document.get("id", ""),
        }

    def _apply_diversity_filter(
        self, results: List[Dict[str, Any]], correlation_id: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Apply diversity filtering to prevent overly similar results.

        Args:
            results: Search results to filter
            correlation_id: Request correlation ID

        Returns:
            Filtered results with improved diversity
        """
        if len(results) <= 1:
            return results

        diverse_results = [results[0]]  # Always include top result

        for candidate in results[1:]:
            is_diverse = True
            candidate_content = candidate.get("content", "").lower()
            candidate_tokens = set(candidate_content.split())

            for existing in diverse_results:
                existing_content = existing.get("content", "").lower()
                existing_tokens = set(existing_content.split())

                # Calculate token overlap similarity
                if candidate_tokens and existing_tokens:
                    intersection = candidate_tokens.intersection(existing_tokens)
                    union = candidate_tokens.union(existing_tokens)
                    jaccard_similarity = len(intersection) / len(union) if union else 0

                    if jaccard_similarity > self.diversity_threshold:
                        is_diverse = False
                        break

            if is_diverse:
                diverse_results.append(candidate)

        filtered_count = len(results) - len(diverse_results)
        if filtered_count > 0:
            logger.info(
                f"Diversity filter removed {filtered_count} similar results",
                extra={"correlation_id": correlation_id},
            )

        return diverse_results

    def build_context_with_tokens(
        self, results: List[Dict[str, Any]], correlation_id: str = ""
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build context string with token-aware truncation.

        Args:
            results: Search results to include in context
            correlation_id: Request correlation ID

        Returns:
            Tuple of (context_string, context_metadata)
        """
        if not results:
            return "", {"token_count": 0, "documents_included": 0}

        context_parts = []
        total_tokens = 0
        documents_included = 0

        for i, doc in enumerate(results):
            content = doc.get("content", "").strip()
            if not content:
                continue

            # Build document section with attribution
            doc_section = f"[Document {i+1}]"

            # Add category and source attribution
            attribution = doc.get("source_attribution", {})
            if attribution.get("category"):
                doc_section += f" ({attribution['category']})"
            if attribution.get("source") and attribution["source"] != "unknown":
                doc_section += f" - Source: {attribution['source']}"

            doc_section += f"\n{content}\n"

            # Count tokens for this section
            section_tokens = len(self.tokenizer.encode(doc_section))

            # Check if adding this section would exceed token limit
            if total_tokens + section_tokens > self.max_context_tokens:
                logger.info(
                    f"Context truncated at document {i+1} due to token limit",
                    extra={
                        "correlation_id": correlation_id,
                        "current_tokens": total_tokens,
                        "section_tokens": section_tokens,
                        "max_tokens": self.max_context_tokens,
                    },
                )
                break

            context_parts.append(doc_section)
            total_tokens += section_tokens
            documents_included += 1

        # Build final context
        if context_parts:
            context = f"Relevant information from knowledge base:\n\n" + "\n".join(
                context_parts
            )
        else:
            context = ""

        metadata = {
            "token_count": total_tokens,
            "documents_included": documents_included,
            "documents_available": len(results),
            "truncated": documents_included < len(results),
        }

        logger.info(
            f"Context built with token awareness",
            extra={"correlation_id": correlation_id, **metadata},
        )

        return context, metadata
