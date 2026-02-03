"""
GROUNDED Knowledge Repository - Data access layer with tenant isolation.

Provides a repository pattern for knowledge operations that enforces
tenant isolation and provides a clean interface for the service layer.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from grounded.knowledge.exceptions import (
    KnowledgeBaseNotFoundError,
    KnowledgeSourceNotFoundError,
    KnowledgeItemNotFoundError,
    DuplicateKnowledgeBaseError,
    DuplicateKnowledgeSourceError,
    TenantIsolationError,
    StorageError,
)
from grounded.knowledge.models import (
    KnowledgeBase,
    KnowledgeBaseStatus,
    KnowledgeSource,
    KnowledgeSourceType,
    KnowledgeItem,
    KnowledgeItemStatus,
    KnowledgeQuery,
    RetrievalResults,
)
from grounded.knowledge.storage import get_storage, BaseKnowledgeStorage


class KnowledgeRepository:
    """
    Repository for knowledge data access with tenant isolation.

    Provides CRUD operations for knowledge bases, sources, and items
    while enforcing tenant boundaries and providing clean error handling.

    Example:
        repo = KnowledgeRepository()

        # Create a knowledge base
        base = repo.create_knowledge_base(
            name="Company Knowledge",
            owner_type="organization",
            owner_id="org-123",
        )

        # Create a source
        source = repo.create_source(
            base_id=base.base_id,
            name="HR Policies",
        )

        # Add an item
        item = repo.create_item(
            base_id=base.base_id,
            source_id=source.source_id,
            content="Employees receive 20 vacation days...",
            title="Vacation Policy",
        )
    """

    def __init__(self, storage: Optional[BaseKnowledgeStorage] = None):
        """
        Initialize the repository.

        Args:
            storage: Optional storage backend. Uses default if not provided.
        """
        self._storage = storage or get_storage()

    @property
    def storage(self) -> BaseKnowledgeStorage:
        """Get the storage backend."""
        return self._storage

    # Knowledge Base operations

    def create_knowledge_base(
        self,
        name: str,
        owner_type: str,
        owner_id: str,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        base_id: Optional[str] = None,
    ) -> KnowledgeBase:
        """
        Create a new knowledge base.

        Args:
            name: Human-readable name
            owner_type: Type of owner (e.g., "organization", "project", "user")
            owner_id: ID of the owner entity
            description: Optional description
            metadata: Optional custom metadata
            base_id: Optional custom base ID (generated if not provided)

        Returns:
            Created KnowledgeBase

        Raises:
            DuplicateKnowledgeBaseError: If base_id already exists
            StorageError: If storage operation fails
        """
        base = KnowledgeBase(
            name=name,
            owner_type=owner_type,
            owner_id=owner_id,
            description=description,
            metadata=metadata or {},
        )

        if base_id:
            base.base_id = base_id
            if self._storage.knowledge_base_exists(base_id):
                raise DuplicateKnowledgeBaseError(base_id)

        if not self._storage.store_knowledge_base(base):
            raise StorageError(
                message=f"Failed to store knowledge base '{name}'",
                operation="create_knowledge_base",
            )

        return base

    def get_knowledge_base(self, base_id: str) -> KnowledgeBase:
        """
        Get a knowledge base by ID.

        Args:
            base_id: The knowledge base ID

        Returns:
            KnowledgeBase

        Raises:
            KnowledgeBaseNotFoundError: If not found
        """
        base = self._storage.get_knowledge_base(base_id)
        if base is None:
            raise KnowledgeBaseNotFoundError(base_id)
        return base

    def get_knowledge_base_or_none(self, base_id: str) -> Optional[KnowledgeBase]:
        """
        Get a knowledge base by ID, returning None if not found.

        Args:
            base_id: The knowledge base ID

        Returns:
            KnowledgeBase or None
        """
        return self._storage.get_knowledge_base(base_id)

    def update_knowledge_base(
        self,
        base_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[KnowledgeBaseStatus] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeBase:
        """
        Update a knowledge base.

        Args:
            base_id: The knowledge base ID
            name: Optional new name
            description: Optional new description
            status: Optional new status
            metadata: Optional metadata to merge

        Returns:
            Updated KnowledgeBase

        Raises:
            KnowledgeBaseNotFoundError: If not found
            StorageError: If storage operation fails
        """
        base = self.get_knowledge_base(base_id)

        if name is not None:
            base.name = name
        if description is not None:
            base.description = description
        if status is not None:
            base.status = status
        if metadata is not None:
            base.metadata.update(metadata)

        base.updated_at = datetime.utcnow()

        if not self._storage.update_knowledge_base(base):
            raise StorageError(
                message=f"Failed to update knowledge base '{base_id}'",
                operation="update_knowledge_base",
            )

        return base

    def delete_knowledge_base(self, base_id: str) -> bool:
        """
        Delete a knowledge base and all its contents.

        Args:
            base_id: The knowledge base ID

        Returns:
            True if deleted

        Raises:
            KnowledgeBaseNotFoundError: If not found
        """
        if not self._storage.knowledge_base_exists(base_id):
            raise KnowledgeBaseNotFoundError(base_id)

        return self._storage.delete_knowledge_base(base_id)

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
            List of KnowledgeBases
        """
        return self._storage.list_knowledge_bases(
            owner_type=owner_type,
            owner_id=owner_id,
            limit=limit,
            offset=offset,
        )

    # Knowledge Source operations

    def create_source(
        self,
        base_id: str,
        name: str,
        description: str = "",
        source_type: KnowledgeSourceType = KnowledgeSourceType.DOCUMENT,
        source_uri: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        source_id: Optional[str] = None,
    ) -> KnowledgeSource:
        """
        Create a new knowledge source.

        Args:
            base_id: Parent knowledge base ID
            name: Human-readable name
            description: Optional description
            source_type: Type of source
            source_uri: Optional URI to original source
            metadata: Optional custom metadata
            source_id: Optional custom source ID

        Returns:
            Created KnowledgeSource

        Raises:
            KnowledgeBaseNotFoundError: If base not found
            DuplicateKnowledgeSourceError: If source_id already exists
            StorageError: If storage operation fails
        """
        # Verify base exists
        self.get_knowledge_base(base_id)

        source = KnowledgeSource(
            base_id=base_id,
            name=name,
            description=description,
            source_type=source_type,
            source_uri=source_uri,
            metadata=metadata or {},
        )

        if source_id:
            source.source_id = source_id
            if self._storage.source_exists(source_id, base_id):
                raise DuplicateKnowledgeSourceError(source_id, base_id)

        if not self._storage.store_source(source):
            raise StorageError(
                message=f"Failed to store source '{name}' in base '{base_id}'",
                operation="create_source",
            )

        return source

    def get_source(self, source_id: str, base_id: str) -> KnowledgeSource:
        """
        Get a source by ID within a base.

        Args:
            source_id: The source ID
            base_id: The knowledge base ID (for tenant isolation)

        Returns:
            KnowledgeSource

        Raises:
            KnowledgeSourceNotFoundError: If not found
        """
        source = self._storage.get_source(source_id, base_id)
        if source is None:
            raise KnowledgeSourceNotFoundError(source_id, base_id)
        return source

    def get_source_or_none(self, source_id: str, base_id: str) -> Optional[KnowledgeSource]:
        """
        Get a source by ID, returning None if not found.

        Args:
            source_id: The source ID
            base_id: The knowledge base ID

        Returns:
            KnowledgeSource or None
        """
        return self._storage.get_source(source_id, base_id)

    def update_source(
        self,
        source_id: str,
        base_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        source_uri: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeSource:
        """
        Update a knowledge source.

        Args:
            source_id: The source ID
            base_id: The knowledge base ID (for tenant isolation)
            name: Optional new name
            description: Optional new description
            source_uri: Optional new source URI
            metadata: Optional metadata to merge

        Returns:
            Updated KnowledgeSource

        Raises:
            KnowledgeSourceNotFoundError: If not found
            StorageError: If storage operation fails
        """
        source = self.get_source(source_id, base_id)

        if name is not None:
            source.name = name
        if description is not None:
            source.description = description
        if source_uri is not None:
            source.source_uri = source_uri
        if metadata is not None:
            source.metadata.update(metadata)

        source.updated_at = datetime.utcnow()

        if not self._storage.update_source(source):
            raise StorageError(
                message=f"Failed to update source '{source_id}' in base '{base_id}'",
                operation="update_source",
            )

        return source

    def delete_source(self, source_id: str, base_id: str) -> bool:
        """
        Delete a source and all its items.

        Args:
            source_id: The source ID
            base_id: The knowledge base ID (for tenant isolation)

        Returns:
            True if deleted

        Raises:
            KnowledgeSourceNotFoundError: If not found
        """
        if not self._storage.source_exists(source_id, base_id):
            raise KnowledgeSourceNotFoundError(source_id, base_id)

        return self._storage.delete_source(source_id, base_id)

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
            List of KnowledgeSources
        """
        return self._storage.list_sources(base_id, limit=limit, offset=offset)

    # Knowledge Item operations

    def create_item(
        self,
        base_id: str,
        source_id: str,
        content: str,
        title: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        chunk_index: int = 0,
        start_char: int = 0,
        end_char: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
        item_id: Optional[str] = None,
    ) -> KnowledgeItem:
        """
        Create a new knowledge item.

        Args:
            base_id: Parent knowledge base ID
            source_id: Parent source ID
            content: The text content
            title: Optional title
            embedding: Optional embedding vector
            chunk_index: Position if part of larger document
            start_char: Start position in original document
            end_char: End position in original document
            metadata: Optional custom metadata
            item_id: Optional custom item ID

        Returns:
            Created KnowledgeItem

        Raises:
            KnowledgeSourceNotFoundError: If source not found in base
            StorageError: If storage operation fails
        """
        # Verify source exists in base (also validates base exists)
        self.get_source(source_id, base_id)

        status = KnowledgeItemStatus.INDEXED if embedding else KnowledgeItemStatus.PENDING

        item = KnowledgeItem(
            base_id=base_id,
            source_id=source_id,
            content=content,
            title=title,
            embedding=embedding,
            status=status,
            chunk_index=chunk_index,
            start_char=start_char,
            end_char=end_char,
            metadata=metadata or {},
        )

        if item_id:
            item.item_id = item_id

        if not self._storage.store_item(item):
            raise StorageError(
                message=f"Failed to store item in source '{source_id}'",
                operation="create_item",
            )

        return item

    def create_items(
        self,
        items: List[KnowledgeItem],
    ) -> List[KnowledgeItem]:
        """
        Create multiple knowledge items.

        Args:
            items: List of items to create

        Returns:
            List of successfully created items
        """
        stored_count = self._storage.store_items(items)
        if stored_count == len(items):
            return items
        # Return items that were stored (all of them in simple implementation)
        return items[:stored_count]

    def get_item(self, item_id: str, base_id: str) -> KnowledgeItem:
        """
        Get an item by ID within a base.

        Args:
            item_id: The item ID
            base_id: The knowledge base ID (for tenant isolation)

        Returns:
            KnowledgeItem

        Raises:
            KnowledgeItemNotFoundError: If not found
        """
        item = self._storage.get_item(item_id, base_id)
        if item is None:
            raise KnowledgeItemNotFoundError(item_id)
        return item

    def get_item_or_none(self, item_id: str, base_id: str) -> Optional[KnowledgeItem]:
        """
        Get an item by ID, returning None if not found.

        Args:
            item_id: The item ID
            base_id: The knowledge base ID

        Returns:
            KnowledgeItem or None
        """
        return self._storage.get_item(item_id, base_id)

    def update_item(
        self,
        item_id: str,
        base_id: str,
        content: Optional[str] = None,
        title: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        status: Optional[KnowledgeItemStatus] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeItem:
        """
        Update a knowledge item.

        Args:
            item_id: The item ID
            base_id: The knowledge base ID (for tenant isolation)
            content: Optional new content
            title: Optional new title
            embedding: Optional new embedding
            status: Optional new status
            metadata: Optional metadata to merge

        Returns:
            Updated KnowledgeItem

        Raises:
            KnowledgeItemNotFoundError: If not found
            StorageError: If storage operation fails
        """
        item = self.get_item(item_id, base_id)

        if content is not None:
            item.content = content
        if title is not None:
            item.title = title
        if embedding is not None:
            item.embedding = embedding
            item.status = KnowledgeItemStatus.INDEXED
        if status is not None:
            item.status = status
        if metadata is not None:
            item.metadata.update(metadata)

        item.updated_at = datetime.utcnow()

        if not self._storage.update_item(item):
            raise StorageError(
                message=f"Failed to update item '{item_id}' in base '{base_id}'",
                operation="update_item",
            )

        return item

    def delete_item(self, item_id: str, base_id: str) -> bool:
        """
        Delete an item.

        Args:
            item_id: The item ID
            base_id: The knowledge base ID (for tenant isolation)

        Returns:
            True if deleted

        Raises:
            KnowledgeItemNotFoundError: If not found
        """
        if not self._storage.item_exists(item_id, base_id):
            raise KnowledgeItemNotFoundError(item_id)

        return self._storage.delete_item(item_id, base_id)

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
            source_id: Optional source filter
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of KnowledgeItems
        """
        return self._storage.list_items(
            base_id,
            source_id=source_id,
            limit=limit,
            offset=offset,
        )

    # Search operations

    def search(self, query: KnowledgeQuery) -> RetrievalResults:
        """
        Search for items matching the query.

        Args:
            query: The search query with base_id for tenant isolation

        Returns:
            RetrievalResults
        """
        return self._storage.search(query)

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
        return self._storage.search_by_text(
            base_id=base_id,
            text=text,
            limit=limit,
            source_ids=source_ids,
        )

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
        return self._storage.search_by_embedding(
            base_id=base_id,
            embedding=embedding,
            limit=limit,
            min_score=min_score,
            source_ids=source_ids,
        )

    # Statistics

    def count_knowledge_bases(
        self,
        owner_type: Optional[str] = None,
        owner_id: Optional[str] = None,
    ) -> int:
        """Count knowledge bases."""
        return self._storage.count_knowledge_bases(
            owner_type=owner_type,
            owner_id=owner_id,
        )

    def count_sources(self, base_id: str) -> int:
        """Count sources in a knowledge base."""
        return self._storage.count_sources(base_id)

    def count_items(
        self,
        base_id: str,
        source_id: Optional[str] = None,
    ) -> int:
        """Count items in a knowledge base."""
        return self._storage.count_items(base_id, source_id=source_id)

    def get_stats(self, base_id: Optional[str] = None) -> Dict[str, Any]:
        """Get repository statistics."""
        return self._storage.get_stats(base_id)
