"""
GROUNDED Document Storage Base - Protocol and base class for storage backends.

Defines the interface for document storage, enabling pluggable storage
backends (in-memory, vector databases, etc.).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from grounded.core.base import GroundedComponent
from grounded.documents.models import (
    DocumentChunk,
    ProcessedDocument,
    DocumentCollection,
)


@dataclass
class SearchQuery:
    """Query for searching documents."""

    query_text: Optional[str] = None
    query_embedding: Optional[List[float]] = None
    filters: Dict[str, Any] = field(default_factory=dict)
    collection_id: Optional[str] = None
    document_ids: Optional[List[str]] = None
    limit: int = 10
    offset: int = 0
    min_score: float = 0.0
    include_content: bool = True
    include_metadata: bool = True


@dataclass
class SearchResult:
    """A single search result."""

    chunk: DocumentChunk
    score: float
    document_id: str
    highlights: List[str] = field(default_factory=list)

    def to_dict(self, include_embedding: bool = False) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "chunk_id": self.chunk.chunk_id,
            "document_id": self.document_id,
            "content": self.chunk.content,
            "score": self.score,
            "chunk_index": self.chunk.chunk_index,
            "highlights": self.highlights,
            "metadata": self.chunk.metadata,
        }


@dataclass
class SearchResults:
    """Collection of search results."""

    results: List[SearchResult] = field(default_factory=list)
    total_count: int = 0
    query_time_ms: float = 0.0

    @property
    def count(self) -> int:
        """Number of results returned."""
        return len(self.results)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "results": [r.to_dict() for r in self.results],
            "count": self.count,
            "total_count": self.total_count,
            "query_time_ms": self.query_time_ms,
        }


@runtime_checkable
class DocumentStorageProtocol(Protocol):
    """Protocol for document storage backends."""

    @property
    def name(self) -> str:
        """Storage backend name."""
        ...

    def store_document(self, document: ProcessedDocument) -> bool:
        """Store a processed document."""
        ...

    def get_document(self, document_id: str) -> Optional[ProcessedDocument]:
        """Retrieve a document by ID."""
        ...

    def delete_document(self, document_id: str) -> bool:
        """Delete a document by ID."""
        ...

    def search(self, query: SearchQuery) -> SearchResults:
        """Search for chunks matching the query."""
        ...


class BaseDocumentStorage(GroundedComponent, ABC):
    """
    Base class for document storage backends.

    Provides common functionality for storing and retrieving processed
    documents and their chunks.

    Example:
        class PostgresStorage(BaseDocumentStorage):
            @property
            def name(self) -> str:
                return "postgres"

            def store_document(self, document: ProcessedDocument) -> bool:
                # Store in PostgreSQL
                ...

            def search(self, query: SearchQuery) -> SearchResults:
                # Search using pg_vector
                ...
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Storage backend name."""
        ...

    @abstractmethod
    def store_document(self, document: ProcessedDocument) -> bool:
        """
        Store a processed document and its chunks.

        Args:
            document: The processed document to store

        Returns:
            True if storage successful
        """
        ...

    def store_documents(self, documents: List[ProcessedDocument]) -> int:
        """
        Store multiple processed documents.

        Args:
            documents: List of processed documents to store

        Returns:
            Number of documents successfully stored
        """
        stored = 0
        for doc in documents:
            if self.store_document(doc):
                stored += 1
        return stored

    @abstractmethod
    def get_document(self, document_id: str) -> Optional[ProcessedDocument]:
        """
        Retrieve a processed document by ID.

        Args:
            document_id: The document ID

        Returns:
            ProcessedDocument or None if not found
        """
        ...

    @abstractmethod
    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document and its chunks.

        Args:
            document_id: The document ID to delete

        Returns:
            True if deletion successful
        """
        ...

    @abstractmethod
    def get_chunk(self, chunk_id: str) -> Optional[DocumentChunk]:
        """
        Retrieve a specific chunk by ID.

        Args:
            chunk_id: The chunk ID

        Returns:
            DocumentChunk or None if not found
        """
        ...

    @abstractmethod
    def get_chunks_for_document(self, document_id: str) -> List[DocumentChunk]:
        """
        Get all chunks for a document.

        Args:
            document_id: The document ID

        Returns:
            List of chunks
        """
        ...

    @abstractmethod
    def search(self, query: SearchQuery) -> SearchResults:
        """
        Search for chunks matching the query.

        Args:
            query: The search query

        Returns:
            SearchResults with matching chunks
        """
        ...

    def search_by_text(
        self,
        text: str,
        limit: int = 10,
        collection_id: Optional[str] = None,
    ) -> SearchResults:
        """
        Convenience method for text search.

        Args:
            text: Text to search for
            limit: Maximum results
            collection_id: Optional collection filter

        Returns:
            SearchResults
        """
        query = SearchQuery(
            query_text=text,
            limit=limit,
            collection_id=collection_id,
        )
        return self.search(query)

    def search_by_embedding(
        self,
        embedding: List[float],
        limit: int = 10,
        min_score: float = 0.0,
        collection_id: Optional[str] = None,
    ) -> SearchResults:
        """
        Search by embedding vector similarity.

        Args:
            embedding: Query embedding vector
            limit: Maximum results
            min_score: Minimum similarity score
            collection_id: Optional collection filter

        Returns:
            SearchResults
        """
        query = SearchQuery(
            query_embedding=embedding,
            limit=limit,
            min_score=min_score,
            collection_id=collection_id,
        )
        return self.search(query)

    @abstractmethod
    def list_documents(
        self,
        collection_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ProcessedDocument]:
        """
        List stored documents.

        Args:
            collection_id: Optional collection filter
            limit: Maximum documents to return
            offset: Pagination offset

        Returns:
            List of processed documents
        """
        ...

    @abstractmethod
    def count_documents(self, collection_id: Optional[str] = None) -> int:
        """
        Count stored documents.

        Args:
            collection_id: Optional collection filter

        Returns:
            Document count
        """
        ...

    @abstractmethod
    def count_chunks(self, document_id: Optional[str] = None) -> int:
        """
        Count stored chunks.

        Args:
            document_id: Optional document filter

        Returns:
            Chunk count
        """
        ...

    def get_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.

        Returns:
            Dictionary of storage stats
        """
        return {
            "backend": self.name,
            "document_count": self.count_documents(),
            "chunk_count": self.count_chunks(),
        }
