"""
GROUNDED Document Storage - In-Memory Backend.

Provides an in-memory storage implementation for development and testing.
Supports full-text search and vector similarity search.
"""

import math
import re
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set

from grounded.documents.storage.base import (
    BaseDocumentStorage,
    SearchQuery,
    SearchResult,
    SearchResults,
)
from grounded.documents.models import DocumentChunk, ProcessedDocument
from grounded.core.base import ComponentStatus, HealthCheckResult


class InMemoryDocumentStorage(BaseDocumentStorage):
    """
    In-memory storage backend for processed documents.

    Suitable for development, testing, and small-scale deployments.
    Data is not persisted across restarts.

    Features:
    - Full-text search with basic ranking
    - Vector similarity search (cosine similarity)
    - Collection-based organization
    - Thread-safe operations (basic)
    """

    def __init__(self):
        """Initialize the in-memory storage."""
        self._documents: Dict[str, ProcessedDocument] = {}
        self._chunks: Dict[str, DocumentChunk] = {}
        self._document_chunks: Dict[str, List[str]] = defaultdict(list)
        self._collection_documents: Dict[str, Set[str]] = defaultdict(set)

        # Inverted index for text search
        self._text_index: Dict[str, Set[str]] = defaultdict(set)

    @property
    def name(self) -> str:
        return "in_memory"

    async def health_check(self) -> HealthCheckResult:
        """Check storage health."""
        return HealthCheckResult(
            status=ComponentStatus.HEALTHY,
            component_name=self.name,
            message="In-memory storage operational",
            details={
                "document_count": len(self._documents),
                "chunk_count": len(self._chunks),
            },
        )

    def store_document(self, document: ProcessedDocument) -> bool:
        """
        Store a processed document and its chunks.

        Args:
            document: The processed document to store

        Returns:
            True if storage successful
        """
        try:
            doc_id = document.document_id

            # Store document
            self._documents[doc_id] = document

            # Store chunks and build index
            for chunk in document.chunks:
                self._chunks[chunk.chunk_id] = chunk
                self._document_chunks[doc_id].append(chunk.chunk_id)

                # Index chunk content for text search
                self._index_chunk(chunk)

            # Track in collection if specified
            collection_id = document.original_document.metadata.custom.get("collection_id")
            if collection_id:
                self._collection_documents[collection_id].add(doc_id)

            return True

        except Exception:
            return False

    def _index_chunk(self, chunk: DocumentChunk) -> None:
        """Build text index for a chunk."""
        # Tokenize content
        tokens = self._tokenize(chunk.content)
        for token in tokens:
            self._text_index[token].add(chunk.chunk_id)

    def _tokenize(self, text: str) -> Set[str]:
        """Simple tokenization for text indexing."""
        # Lowercase and extract words
        words = re.findall(r'\b\w+\b', text.lower())
        return set(words)

    def get_document(self, document_id: str) -> Optional[ProcessedDocument]:
        """Retrieve a document by ID."""
        return self._documents.get(document_id)

    def delete_document(self, document_id: str) -> bool:
        """Delete a document and its chunks."""
        if document_id not in self._documents:
            return False

        # Remove chunks and their index entries
        chunk_ids = self._document_chunks.get(document_id, [])
        for chunk_id in chunk_ids:
            chunk = self._chunks.get(chunk_id)
            if chunk:
                # Remove from text index
                tokens = self._tokenize(chunk.content)
                for token in tokens:
                    self._text_index[token].discard(chunk_id)

                del self._chunks[chunk_id]

        # Remove document
        del self._documents[document_id]
        if document_id in self._document_chunks:
            del self._document_chunks[document_id]

        # Remove from collections
        for collection_docs in self._collection_documents.values():
            collection_docs.discard(document_id)

        return True

    def get_chunk(self, chunk_id: str) -> Optional[DocumentChunk]:
        """Retrieve a chunk by ID."""
        return self._chunks.get(chunk_id)

    def get_chunks_for_document(self, document_id: str) -> List[DocumentChunk]:
        """Get all chunks for a document."""
        chunk_ids = self._document_chunks.get(document_id, [])
        chunks = [self._chunks[cid] for cid in chunk_ids if cid in self._chunks]
        return sorted(chunks, key=lambda c: c.chunk_index)

    def search(self, query: SearchQuery) -> SearchResults:
        """
        Search for chunks matching the query.

        Supports both text search and vector similarity search.
        """
        start_time = time.time()
        results: List[SearchResult] = []

        # Get candidate chunk IDs
        candidate_ids = self._get_candidates(query)

        # Score and rank candidates
        scored_results = []
        for chunk_id in candidate_ids:
            chunk = self._chunks.get(chunk_id)
            if not chunk:
                continue

            # Apply filters
            if not self._matches_filters(chunk, query):
                continue

            # Calculate score
            score = self._calculate_score(chunk, query)
            if score >= query.min_score:
                scored_results.append((chunk, score))

        # Sort by score descending
        scored_results.sort(key=lambda x: x[1], reverse=True)

        # Apply pagination
        paginated = scored_results[query.offset : query.offset + query.limit]

        # Build results
        for chunk, score in paginated:
            highlights = []
            if query.query_text and query.include_content:
                highlights = self._generate_highlights(chunk.content, query.query_text)

            results.append(
                SearchResult(
                    chunk=chunk,
                    score=score,
                    document_id=chunk.document_id,
                    highlights=highlights,
                )
            )

        query_time_ms = (time.time() - start_time) * 1000

        return SearchResults(
            results=results,
            total_count=len(scored_results),
            query_time_ms=query_time_ms,
        )

    def _get_candidates(self, query: SearchQuery) -> Set[str]:
        """Get candidate chunk IDs based on query."""
        candidates: Optional[Set[str]] = None

        # Filter by collection
        if query.collection_id:
            doc_ids = self._collection_documents.get(query.collection_id, set())
            candidates = set()
            for doc_id in doc_ids:
                candidates.update(self._document_chunks.get(doc_id, []))

        # Filter by document IDs
        if query.document_ids:
            doc_candidates = set()
            for doc_id in query.document_ids:
                doc_candidates.update(self._document_chunks.get(doc_id, []))
            if candidates is None:
                candidates = doc_candidates
            else:
                candidates &= doc_candidates

        # Text search candidates
        if query.query_text:
            tokens = self._tokenize(query.query_text)
            text_candidates: Optional[Set[str]] = None
            for token in tokens:
                token_chunks = self._text_index.get(token, set())
                if text_candidates is None:
                    text_candidates = token_chunks.copy()
                else:
                    # Union for OR-style matching
                    text_candidates |= token_chunks

            if text_candidates:
                if candidates is None:
                    candidates = text_candidates
                else:
                    candidates &= text_candidates

        # If no specific filters, return all chunks
        if candidates is None:
            candidates = set(self._chunks.keys())

        return candidates

    def _matches_filters(self, chunk: DocumentChunk, query: SearchQuery) -> bool:
        """Check if chunk matches query filters."""
        for key, value in query.filters.items():
            chunk_value = chunk.metadata.get(key)
            if chunk_value != value:
                return False
        return True

    def _calculate_score(self, chunk: DocumentChunk, query: SearchQuery) -> float:
        """Calculate relevance score for a chunk."""
        score = 0.0

        # Text relevance score (TF-IDF-like)
        if query.query_text:
            text_score = self._text_similarity(chunk.content, query.query_text)
            score += text_score * 0.5  # Weight text score

        # Vector similarity score
        if query.query_embedding and chunk.embedding:
            vector_score = self._cosine_similarity(chunk.embedding, query.query_embedding)
            score += vector_score * 0.5  # Weight vector score

        # If only one type of search, normalize
        if query.query_text and not query.query_embedding:
            score *= 2
        elif query.query_embedding and not query.query_text:
            score *= 2

        return score

    def _text_similarity(self, content: str, query: str) -> float:
        """Calculate text similarity score."""
        content_tokens = self._tokenize(content)
        query_tokens = self._tokenize(query)

        if not query_tokens:
            return 0.0

        # Count matching tokens
        matches = len(content_tokens & query_tokens)

        # Normalize by query length
        return matches / len(query_tokens)

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def _generate_highlights(self, content: str, query: str) -> List[str]:
        """Generate text highlights for search results."""
        highlights = []
        query_tokens = self._tokenize(query)

        # Find sentences containing query terms
        sentences = re.split(r'[.!?]+', content)
        for sentence in sentences:
            sentence_tokens = self._tokenize(sentence)
            if sentence_tokens & query_tokens:
                highlight = sentence.strip()
                if len(highlight) > 200:
                    highlight = highlight[:200] + "..."
                highlights.append(highlight)
                if len(highlights) >= 3:
                    break

        return highlights

    def list_documents(
        self,
        collection_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ProcessedDocument]:
        """List stored documents."""
        if collection_id:
            doc_ids = list(self._collection_documents.get(collection_id, set()))
        else:
            doc_ids = list(self._documents.keys())

        # Apply pagination
        doc_ids = doc_ids[offset : offset + limit]

        return [self._documents[doc_id] for doc_id in doc_ids if doc_id in self._documents]

    def count_documents(self, collection_id: Optional[str] = None) -> int:
        """Count stored documents."""
        if collection_id:
            return len(self._collection_documents.get(collection_id, set()))
        return len(self._documents)

    def count_chunks(self, document_id: Optional[str] = None) -> int:
        """Count stored chunks."""
        if document_id:
            return len(self._document_chunks.get(document_id, []))
        return len(self._chunks)

    def clear(self) -> None:
        """Clear all stored data."""
        self._documents.clear()
        self._chunks.clear()
        self._document_chunks.clear()
        self._collection_documents.clear()
        self._text_index.clear()
