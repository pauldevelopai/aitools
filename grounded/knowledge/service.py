"""
GROUNDED Knowledge Service - Main orchestrator for knowledge operations.

Provides a unified interface for all knowledge management operations
including storage, retrieval, and answer generation.
"""

from typing import Any, Dict, List, Optional

from grounded.documents.models import Document, DocumentChunk
from grounded.knowledge.exceptions import (
    KnowledgeBaseNotFoundError,
    KnowledgeSourceNotFoundError,
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
    GroundedAnswer,
)
from grounded.knowledge.repository import KnowledgeRepository
from grounded.knowledge.retriever import KnowledgeRetriever
from grounded.knowledge.answerer import KnowledgeAnswerer
from grounded.knowledge.storage import get_storage, BaseKnowledgeStorage


class KnowledgeService:
    """
    Main orchestrator for knowledge management operations.

    Provides a unified, high-level interface for:
    - Creating and managing knowledge bases (multi-tenant containers)
    - Creating and managing knowledge sources
    - Adding and indexing knowledge items
    - Semantic and hybrid search
    - Grounded answer generation with citations

    Example:
        service = KnowledgeService()
        await service.initialize()

        # Create knowledge base
        base = service.create_knowledge_base(
            name="Company Knowledge",
            owner_type="organization",
            owner_id="org-123",
        )

        # Create a source
        source = service.create_source(
            base_id=base.base_id,
            name="HR Policies",
        )

        # Add knowledge
        service.add_knowledge(
            base_id=base.base_id,
            source_id=source.source_id,
            content="Employees receive 20 vacation days per year...",
            title="Vacation Policy",
        )

        # Search
        results = service.search(base.base_id, "vacation days")

        # Get grounded answer
        answer = service.get_answer(base.base_id, "How many vacation days?")
    """

    def __init__(self, storage: Optional[BaseKnowledgeStorage] = None):
        """
        Initialize the knowledge service.

        Args:
            storage: Optional storage backend. Uses default if not provided.
        """
        self._storage = storage or get_storage()
        self._repository = KnowledgeRepository(self._storage)
        self._retriever = KnowledgeRetriever(self._repository)
        self._answerer = KnowledgeAnswerer(self._repository, self._retriever)
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Check if the service is initialized."""
        return self._initialized

    @property
    def repository(self) -> KnowledgeRepository:
        """Get the repository for direct access."""
        return self._repository

    @property
    def retriever(self) -> KnowledgeRetriever:
        """Get the retriever for direct access."""
        return self._retriever

    @property
    def answerer(self) -> KnowledgeAnswerer:
        """Get the answerer for direct access."""
        return self._answerer

    async def initialize(self) -> None:
        """
        Initialize the service and its components.

        Sets up the retriever and answerer with AI providers.
        """
        await self._retriever.initialize()
        await self._answerer.initialize()
        self._initialized = True

    def _ensure_initialized(self) -> None:
        """Ensure the service is initialized."""
        if not self._initialized:
            import asyncio
            asyncio.get_event_loop().run_until_complete(self.initialize())

    # Knowledge Base operations

    def create_knowledge_base(
        self,
        name: str,
        owner_type: str,
        owner_id: str,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeBase:
        """
        Create a new knowledge base.

        Args:
            name: Human-readable name
            owner_type: Type of owner (e.g., "organization", "project", "user")
            owner_id: ID of the owner entity
            description: Optional description
            metadata: Optional custom metadata

        Returns:
            Created KnowledgeBase
        """
        return self._repository.create_knowledge_base(
            name=name,
            owner_type=owner_type,
            owner_id=owner_id,
            description=description,
            metadata=metadata,
        )

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
        return self._repository.get_knowledge_base(base_id)

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
        return self._repository.list_knowledge_bases(
            owner_type=owner_type,
            owner_id=owner_id,
            limit=limit,
            offset=offset,
        )

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
        """
        return self._repository.update_knowledge_base(
            base_id=base_id,
            name=name,
            description=description,
            status=status,
            metadata=metadata,
        )

    def delete_knowledge_base(self, base_id: str) -> bool:
        """
        Delete a knowledge base and all its contents.

        Args:
            base_id: The knowledge base ID

        Returns:
            True if deleted
        """
        return self._repository.delete_knowledge_base(base_id)

    # Knowledge Source operations

    def create_source(
        self,
        base_id: str,
        name: str,
        description: str = "",
        source_type: KnowledgeSourceType = KnowledgeSourceType.DOCUMENT,
        source_uri: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
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

        Returns:
            Created KnowledgeSource
        """
        return self._repository.create_source(
            base_id=base_id,
            name=name,
            description=description,
            source_type=source_type,
            source_uri=source_uri,
            metadata=metadata,
        )

    def get_source(self, source_id: str, base_id: str) -> KnowledgeSource:
        """
        Get a source by ID within a base.

        Args:
            source_id: The source ID
            base_id: The knowledge base ID

        Returns:
            KnowledgeSource

        Raises:
            KnowledgeSourceNotFoundError: If not found
        """
        return self._repository.get_source(source_id, base_id)

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
        return self._repository.list_sources(base_id, limit=limit, offset=offset)

    def delete_source(self, source_id: str, base_id: str) -> bool:
        """
        Delete a source and all its items.

        Args:
            source_id: The source ID
            base_id: The knowledge base ID

        Returns:
            True if deleted
        """
        return self._repository.delete_source(source_id, base_id)

    # Knowledge Item operations

    def add_knowledge(
        self,
        base_id: str,
        source_id: str,
        content: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        generate_embedding: bool = True,
    ) -> KnowledgeItem:
        """
        Add a knowledge item to a source.

        Args:
            base_id: Parent knowledge base ID
            source_id: Parent source ID
            content: The text content
            title: Optional title
            metadata: Optional custom metadata
            generate_embedding: Whether to generate embedding

        Returns:
            Created KnowledgeItem
        """
        self._ensure_initialized()

        # Create item
        item = self._repository.create_item(
            base_id=base_id,
            source_id=source_id,
            content=content,
            title=title,
            metadata=metadata,
        )

        # Generate embedding if requested
        if generate_embedding:
            item = self._retriever.embed_item(item)
            item.status = KnowledgeItemStatus.INDEXED
            self._repository.update_item(
                item_id=item.item_id,
                base_id=base_id,
                embedding=item.embedding,
                status=item.status,
            )

        return item

    def add_knowledge_batch(
        self,
        base_id: str,
        source_id: str,
        contents: List[Dict[str, Any]],
        generate_embeddings: bool = True,
    ) -> List[KnowledgeItem]:
        """
        Add multiple knowledge items to a source.

        Args:
            base_id: Parent knowledge base ID
            source_id: Parent source ID
            contents: List of dicts with 'content', optional 'title', 'metadata'
            generate_embeddings: Whether to generate embeddings

        Returns:
            List of created KnowledgeItems
        """
        self._ensure_initialized()

        items = []
        for i, content_data in enumerate(contents):
            item = KnowledgeItem(
                base_id=base_id,
                source_id=source_id,
                content=content_data["content"],
                title=content_data.get("title"),
                metadata=content_data.get("metadata", {}),
                chunk_index=i,
            )
            items.append(item)

        # Generate embeddings in batch
        if generate_embeddings:
            items = self._retriever.embed_items(items)
            for item in items:
                item.status = KnowledgeItemStatus.INDEXED

        # Store items
        self._repository.create_items(items)

        return items

    def add_document(
        self,
        base_id: str,
        source_id: str,
        document: Document,
        chunks: Optional[List[DocumentChunk]] = None,
        generate_embeddings: bool = True,
    ) -> List[KnowledgeItem]:
        """
        Add a document to a knowledge source.

        Can accept pre-chunked content or the full document.

        Args:
            base_id: Parent knowledge base ID
            source_id: Parent source ID
            document: The document to add
            chunks: Optional pre-chunked content
            generate_embeddings: Whether to generate embeddings

        Returns:
            List of created KnowledgeItems
        """
        self._ensure_initialized()

        items = []

        if chunks:
            # Use provided chunks
            for chunk in chunks:
                item = KnowledgeItem(
                    base_id=base_id,
                    source_id=source_id,
                    content=chunk.content,
                    title=document.metadata.title,
                    chunk_index=chunk.chunk_index,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                    metadata={
                        "document_id": document.document_id,
                        "document_type": document.document_type.value,
                        **chunk.metadata,
                    },
                )
                items.append(item)
        else:
            # Store entire document as one item
            item = KnowledgeItem(
                base_id=base_id,
                source_id=source_id,
                content=document.content,
                title=document.metadata.title,
                metadata={
                    "document_id": document.document_id,
                    "document_type": document.document_type.value,
                    "source": document.metadata.source,
                    "source_url": document.metadata.source_url,
                },
            )
            items.append(item)

        # Generate embeddings
        if generate_embeddings:
            items = self._retriever.embed_items(items)
            for item in items:
                item.status = KnowledgeItemStatus.INDEXED

        # Store items
        self._repository.create_items(items)

        return items

    def get_item(self, item_id: str, base_id: str) -> KnowledgeItem:
        """
        Get a knowledge item by ID.

        Args:
            item_id: The item ID
            base_id: The knowledge base ID

        Returns:
            KnowledgeItem
        """
        return self._repository.get_item(item_id, base_id)

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
        return self._repository.list_items(
            base_id,
            source_id=source_id,
            limit=limit,
            offset=offset,
        )

    def delete_item(self, item_id: str, base_id: str) -> bool:
        """
        Delete a knowledge item.

        Args:
            item_id: The item ID
            base_id: The knowledge base ID

        Returns:
            True if deleted
        """
        return self._repository.delete_item(item_id, base_id)

    # Search operations

    def search(
        self,
        base_id: str,
        query: str,
        limit: int = 10,
        source_ids: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0,
        search_type: str = "hybrid",
    ) -> RetrievalResults:
        """
        Search for relevant knowledge items.

        Args:
            base_id: Knowledge base to search
            query: Search query
            limit: Maximum results
            source_ids: Optional source filter
            filters: Optional metadata filters
            min_score: Minimum relevance score
            search_type: "text", "semantic", or "hybrid" (default)

        Returns:
            RetrievalResults
        """
        self._ensure_initialized()

        if search_type == "text":
            return self._retriever.search(
                base_id=base_id,
                query_text=query,
                limit=limit,
                source_ids=source_ids,
                filters=filters,
                min_score=min_score,
            )
        elif search_type == "semantic":
            return self._retriever.semantic_search(
                base_id=base_id,
                query_text=query,
                limit=limit,
                source_ids=source_ids,
                filters=filters,
                min_score=min_score,
            )
        else:  # hybrid
            return self._retriever.hybrid_search(
                base_id=base_id,
                query_text=query,
                limit=limit,
                source_ids=source_ids,
                filters=filters,
                min_score=min_score,
            )

    # Answer generation

    def get_answer(
        self,
        base_id: str,
        query: str,
        limit: int = 5,
        source_ids: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> GroundedAnswer:
        """
        Get a grounded answer for a query.

        Args:
            base_id: Knowledge base to search
            query: The question to answer
            limit: Maximum number of sources to use
            source_ids: Optional source filter
            filters: Optional metadata filters

        Returns:
            GroundedAnswer with answer text and citations
        """
        self._ensure_initialized()

        return self._answerer.get_answer(
            base_id=base_id,
            query=query,
            limit=limit,
            source_ids=source_ids,
            filters=filters,
        )

    # Statistics and utilities

    def get_stats(self, base_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get service statistics.

        Args:
            base_id: Optional knowledge base to get stats for

        Returns:
            Dictionary of statistics
        """
        stats = {
            "initialized": self._initialized,
            "storage": self._repository.get_stats(base_id),
        }

        if base_id:
            stats["base_id"] = base_id
            stats["source_count"] = self._repository.count_sources(base_id)
            stats["item_count"] = self._repository.count_items(base_id)
        else:
            stats["knowledge_base_count"] = self._repository.count_knowledge_bases()

        return stats

    def count_items(
        self,
        base_id: str,
        source_id: Optional[str] = None,
    ) -> int:
        """Count items in a knowledge base."""
        return self._repository.count_items(base_id, source_id=source_id)

    def count_sources(self, base_id: str) -> int:
        """Count sources in a knowledge base."""
        return self._repository.count_sources(base_id)
