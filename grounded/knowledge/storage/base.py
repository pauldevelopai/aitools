"""
GROUNDED Knowledge Storage Base - Protocol and base class for storage backends.

Defines the interface for knowledge storage, enabling pluggable storage
backends (in-memory, vector databases, etc.).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from grounded.core.base import GroundedComponent
from grounded.knowledge.models import (
    KnowledgeBase,
    KnowledgeSource,
    KnowledgeItem,
    KnowledgeQuery,
    RetrievalResult,
    RetrievalResults,
)


@runtime_checkable
class KnowledgeStorageProtocol(Protocol):
    """Protocol for knowledge storage backends."""

    @property
    def name(self) -> str:
        """Storage backend name."""
        ...

    # Knowledge Base operations
    def store_knowledge_base(self, base: KnowledgeBase) -> bool:
        """Store a knowledge base."""
        ...

    def get_knowledge_base(self, base_id: str) -> Optional[KnowledgeBase]:
        """Retrieve a knowledge base by ID."""
        ...

    def delete_knowledge_base(self, base_id: str) -> bool:
        """Delete a knowledge base and all its contents."""
        ...

    def list_knowledge_bases(
        self,
        owner_type: Optional[str] = None,
        owner_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[KnowledgeBase]:
        """List knowledge bases with optional filtering."""
        ...

    # Knowledge Source operations
    def store_source(self, source: KnowledgeSource) -> bool:
        """Store a knowledge source."""
        ...

    def get_source(self, source_id: str, base_id: str) -> Optional[KnowledgeSource]:
        """Retrieve a source by ID within a base."""
        ...

    def delete_source(self, source_id: str, base_id: str) -> bool:
        """Delete a source and all its items."""
        ...

    def list_sources(
        self,
        base_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[KnowledgeSource]:
        """List sources within a knowledge base."""
        ...

    # Knowledge Item operations
    def store_item(self, item: KnowledgeItem) -> bool:
        """Store a knowledge item."""
        ...

    def store_items(self, items: List[KnowledgeItem]) -> int:
        """Store multiple items. Returns count of successfully stored items."""
        ...

    def get_item(self, item_id: str, base_id: str) -> Optional[KnowledgeItem]:
        """Retrieve an item by ID within a base."""
        ...

    def delete_item(self, item_id: str, base_id: str) -> bool:
        """Delete an item."""
        ...

    def list_items(
        self,
        base_id: str,
        source_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[KnowledgeItem]:
        """List items within a base, optionally filtered by source."""
        ...

    # Search operations
    def search(self, query: KnowledgeQuery) -> RetrievalResults:
        """Search for items matching the query within a knowledge base."""
        ...


class BaseKnowledgeStorage(GroundedComponent, ABC):
    """
    Base class for knowledge storage backends.

    Provides common functionality for storing and retrieving knowledge bases,
    sources, and items with tenant isolation.

    Example:
        class PostgresKnowledgeStorage(BaseKnowledgeStorage):
            @property
            def name(self) -> str:
                return "postgres"

            def store_knowledge_base(self, base: KnowledgeBase) -> bool:
                # Store in PostgreSQL
                ...
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Storage backend name."""
        ...

    # Knowledge Base operations
    @abstractmethod
    def store_knowledge_base(self, base: KnowledgeBase) -> bool:
        """
        Store a knowledge base.

        Args:
            base: The knowledge base to store

        Returns:
            True if storage successful
        """
        ...

    @abstractmethod
    def get_knowledge_base(self, base_id: str) -> Optional[KnowledgeBase]:
        """
        Retrieve a knowledge base by ID.

        Args:
            base_id: The knowledge base ID

        Returns:
            KnowledgeBase or None if not found
        """
        ...

    def update_knowledge_base(self, base: KnowledgeBase) -> bool:
        """
        Update an existing knowledge base.

        Args:
            base: The knowledge base to update

        Returns:
            True if update successful
        """
        return self.store_knowledge_base(base)

    @abstractmethod
    def delete_knowledge_base(self, base_id: str) -> bool:
        """
        Delete a knowledge base and all its contents.

        Args:
            base_id: The knowledge base ID to delete

        Returns:
            True if deletion successful
        """
        ...

    @abstractmethod
    def list_knowledge_bases(
        self,
        owner_type: Optional[str] = None,
        owner_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[KnowledgeBase]:
        """
        List knowledge bases with optional filtering.

        Args:
            owner_type: Filter by owner type
            owner_id: Filter by owner ID
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of knowledge bases
        """
        ...

    def knowledge_base_exists(self, base_id: str) -> bool:
        """
        Check if a knowledge base exists.

        Args:
            base_id: The knowledge base ID

        Returns:
            True if exists
        """
        return self.get_knowledge_base(base_id) is not None

    # Knowledge Source operations
    @abstractmethod
    def store_source(self, source: KnowledgeSource) -> bool:
        """
        Store a knowledge source.

        Args:
            source: The source to store

        Returns:
            True if storage successful
        """
        ...

    @abstractmethod
    def get_source(self, source_id: str, base_id: str) -> Optional[KnowledgeSource]:
        """
        Retrieve a source by ID within a base.

        Args:
            source_id: The source ID
            base_id: The knowledge base ID (for tenant isolation)

        Returns:
            KnowledgeSource or None if not found
        """
        ...

    def update_source(self, source: KnowledgeSource) -> bool:
        """
        Update an existing source.

        Args:
            source: The source to update

        Returns:
            True if update successful
        """
        return self.store_source(source)

    @abstractmethod
    def delete_source(self, source_id: str, base_id: str) -> bool:
        """
        Delete a source and all its items.

        Args:
            source_id: The source ID to delete
            base_id: The knowledge base ID (for tenant isolation)

        Returns:
            True if deletion successful
        """
        ...

    @abstractmethod
    def list_sources(
        self,
        base_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[KnowledgeSource]:
        """
        List sources within a knowledge base.

        Args:
            base_id: The knowledge base ID
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of sources
        """
        ...

    def source_exists(self, source_id: str, base_id: str) -> bool:
        """
        Check if a source exists.

        Args:
            source_id: The source ID
            base_id: The knowledge base ID

        Returns:
            True if exists
        """
        return self.get_source(source_id, base_id) is not None

    # Knowledge Item operations
    @abstractmethod
    def store_item(self, item: KnowledgeItem) -> bool:
        """
        Store a knowledge item.

        Args:
            item: The item to store

        Returns:
            True if storage successful
        """
        ...

    def store_items(self, items: List[KnowledgeItem]) -> int:
        """
        Store multiple items.

        Args:
            items: List of items to store

        Returns:
            Number of items successfully stored
        """
        stored = 0
        for item in items:
            if self.store_item(item):
                stored += 1
        return stored

    @abstractmethod
    def get_item(self, item_id: str, base_id: str) -> Optional[KnowledgeItem]:
        """
        Retrieve an item by ID within a base.

        Args:
            item_id: The item ID
            base_id: The knowledge base ID (for tenant isolation)

        Returns:
            KnowledgeItem or None if not found
        """
        ...

    def update_item(self, item: KnowledgeItem) -> bool:
        """
        Update an existing item.

        Args:
            item: The item to update

        Returns:
            True if update successful
        """
        return self.store_item(item)

    @abstractmethod
    def delete_item(self, item_id: str, base_id: str) -> bool:
        """
        Delete an item.

        Args:
            item_id: The item ID to delete
            base_id: The knowledge base ID (for tenant isolation)

        Returns:
            True if deletion successful
        """
        ...

    @abstractmethod
    def list_items(
        self,
        base_id: str,
        source_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[KnowledgeItem]:
        """
        List items within a base, optionally filtered by source.

        Args:
            base_id: The knowledge base ID
            source_id: Optional source ID filter
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of items
        """
        ...

    def item_exists(self, item_id: str, base_id: str) -> bool:
        """
        Check if an item exists.

        Args:
            item_id: The item ID
            base_id: The knowledge base ID

        Returns:
            True if exists
        """
        return self.get_item(item_id, base_id) is not None

    # Search operations
    @abstractmethod
    def search(self, query: KnowledgeQuery) -> RetrievalResults:
        """
        Search for items matching the query within a knowledge base.

        Args:
            query: The search query with base_id for tenant isolation

        Returns:
            RetrievalResults with matching items
        """
        ...

    def search_by_text(
        self,
        base_id: str,
        text: str,
        limit: int = 10,
        source_ids: Optional[List[str]] = None,
    ) -> RetrievalResults:
        """
        Convenience method for text search.

        Args:
            base_id: The knowledge base ID
            text: Text to search for
            limit: Maximum results
            source_ids: Optional source filter

        Returns:
            RetrievalResults
        """
        query = KnowledgeQuery(
            base_id=base_id,
            query_text=text,
            limit=limit,
            source_ids=source_ids,
        )
        return self.search(query)

    def search_by_embedding(
        self,
        base_id: str,
        embedding: List[float],
        limit: int = 10,
        min_score: float = 0.0,
        source_ids: Optional[List[str]] = None,
    ) -> RetrievalResults:
        """
        Search by embedding vector similarity.

        Args:
            base_id: The knowledge base ID
            embedding: Query embedding vector
            limit: Maximum results
            min_score: Minimum similarity score
            source_ids: Optional source filter

        Returns:
            RetrievalResults
        """
        query = KnowledgeQuery(
            base_id=base_id,
            query_embedding=embedding,
            limit=limit,
            min_score=min_score,
            source_ids=source_ids,
        )
        return self.search(query)

    # Statistics
    @abstractmethod
    def count_knowledge_bases(
        self,
        owner_type: Optional[str] = None,
        owner_id: Optional[str] = None,
    ) -> int:
        """
        Count knowledge bases.

        Args:
            owner_type: Optional owner type filter
            owner_id: Optional owner ID filter

        Returns:
            Count of knowledge bases
        """
        ...

    @abstractmethod
    def count_sources(self, base_id: str) -> int:
        """
        Count sources in a knowledge base.

        Args:
            base_id: The knowledge base ID

        Returns:
            Count of sources
        """
        ...

    @abstractmethod
    def count_items(
        self,
        base_id: str,
        source_id: Optional[str] = None,
    ) -> int:
        """
        Count items in a knowledge base.

        Args:
            base_id: The knowledge base ID
            source_id: Optional source filter

        Returns:
            Count of items
        """
        ...

    def get_stats(self, base_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get storage statistics.

        Args:
            base_id: Optional knowledge base to get stats for

        Returns:
            Dictionary of storage stats
        """
        if base_id:
            return {
                "backend": self.name,
                "base_id": base_id,
                "source_count": self.count_sources(base_id),
                "item_count": self.count_items(base_id),
            }
        return {
            "backend": self.name,
            "knowledge_base_count": self.count_knowledge_bases(),
        }
