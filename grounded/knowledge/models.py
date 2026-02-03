"""
GROUNDED Knowledge Models - Data structures for knowledge management.

Defines the core data models for the knowledge and retrieval subsystem:
- KnowledgeBase: Top-level tenant container
- KnowledgeSource: Collection within a base (document, archive, etc.)
- KnowledgeItem: Individual searchable unit with embedding
- KnowledgeQuery: Search query with filters
- RetrievalResult: Search result with score
- GroundedAnswer: Answer with citations
- Citation: Source attribution
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class KnowledgeBaseStatus(Enum):
    """Status of a knowledge base."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class KnowledgeSourceType(Enum):
    """Types of knowledge sources."""

    DOCUMENT = "document"
    DOCUMENT_COLLECTION = "document_collection"
    MANUAL = "manual"
    API = "api"
    WEB_SCRAPE = "web_scrape"
    DATABASE = "database"
    OTHER = "other"


class KnowledgeItemStatus(Enum):
    """Status of a knowledge item."""

    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


@dataclass
class KnowledgeBase:
    """
    Top-level tenant container for knowledge management.

    A KnowledgeBase is the primary isolation boundary for multi-tenant
    knowledge storage. Each base has an owner (organization, project, user)
    and contains multiple KnowledgeSources.

    Attributes:
        base_id: Unique identifier for the knowledge base
        name: Human-readable name
        description: Optional description
        owner_type: Type of owner (e.g., "organization", "project", "user")
        owner_id: ID of the owner entity
        status: Current status of the knowledge base
        metadata: Additional custom metadata
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    name: str
    owner_type: str
    owner_id: str
    base_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    status: KnowledgeBaseStatus = KnowledgeBaseStatus.ACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "base_id": self.base_id,
            "name": self.name,
            "description": self.description,
            "owner_type": self.owner_type,
            "owner_id": self.owner_id,
            "status": self.status.value,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeBase":
        """Create from dictionary representation."""
        return cls(
            base_id=data["base_id"],
            name=data["name"],
            description=data.get("description", ""),
            owner_type=data["owner_type"],
            owner_id=data["owner_id"],
            status=KnowledgeBaseStatus(data.get("status", "active")),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else data.get("created_at", datetime.utcnow()),
            updated_at=datetime.fromisoformat(data["updated_at"]) if isinstance(data.get("updated_at"), str) else data.get("updated_at", datetime.utcnow()),
        )


@dataclass
class KnowledgeSource:
    """
    A collection of knowledge items within a knowledge base.

    KnowledgeSources represent logical groupings of knowledge items,
    such as a document, a set of meeting notes, or an FAQ collection.

    Attributes:
        source_id: Unique identifier for the source
        base_id: Parent knowledge base ID
        name: Human-readable name
        description: Optional description
        source_type: Type of source (document, manual, etc.)
        source_uri: Optional URI pointing to the original source
        metadata: Additional custom metadata
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    base_id: str
    name: str
    source_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    source_type: KnowledgeSourceType = KnowledgeSourceType.DOCUMENT
    source_uri: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "source_id": self.source_id,
            "base_id": self.base_id,
            "name": self.name,
            "description": self.description,
            "source_type": self.source_type.value,
            "source_uri": self.source_uri,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeSource":
        """Create from dictionary representation."""
        return cls(
            source_id=data["source_id"],
            base_id=data["base_id"],
            name=data["name"],
            description=data.get("description", ""),
            source_type=KnowledgeSourceType(data.get("source_type", "document")),
            source_uri=data.get("source_uri"),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else data.get("created_at", datetime.utcnow()),
            updated_at=datetime.fromisoformat(data["updated_at"]) if isinstance(data.get("updated_at"), str) else data.get("updated_at", datetime.utcnow()),
        )


@dataclass
class KnowledgeItem:
    """
    An individual searchable unit of knowledge with embedding.

    KnowledgeItems are the atomic units of knowledge storage and retrieval.
    Each item contains content text, an embedding vector for semantic search,
    and metadata for filtering.

    Attributes:
        item_id: Unique identifier for the item
        source_id: Parent source ID
        base_id: Parent knowledge base ID (denormalized for query efficiency)
        content: The actual text content
        title: Optional title or heading
        embedding: Vector embedding for semantic search
        status: Processing status
        chunk_index: Position if this is part of a larger document
        start_char: Start character position in original document
        end_char: End character position in original document
        metadata: Additional custom metadata
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    source_id: str
    base_id: str
    content: str
    item_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: Optional[str] = None
    embedding: Optional[List[float]] = None
    status: KnowledgeItemStatus = KnowledgeItemStatus.PENDING
    chunk_index: int = 0
    start_char: int = 0
    end_char: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def has_embedding(self) -> bool:
        """Check if this item has an embedding."""
        return self.embedding is not None and len(self.embedding) > 0

    @property
    def character_count(self) -> int:
        """Number of characters in the content."""
        return len(self.content)

    @property
    def word_count(self) -> int:
        """Approximate word count in the content."""
        return len(self.content.split())

    def to_dict(self, include_embedding: bool = False) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "item_id": self.item_id,
            "source_id": self.source_id,
            "base_id": self.base_id,
            "content": self.content,
            "title": self.title,
            "has_embedding": self.has_embedding,
            "status": self.status.value,
            "chunk_index": self.chunk_index,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "character_count": self.character_count,
            "word_count": self.word_count,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if include_embedding and self.embedding:
            result["embedding"] = self.embedding
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeItem":
        """Create from dictionary representation."""
        return cls(
            item_id=data["item_id"],
            source_id=data["source_id"],
            base_id=data["base_id"],
            content=data["content"],
            title=data.get("title"),
            embedding=data.get("embedding"),
            status=KnowledgeItemStatus(data.get("status", "pending")),
            chunk_index=data.get("chunk_index", 0),
            start_char=data.get("start_char", 0),
            end_char=data.get("end_char", 0),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else data.get("created_at", datetime.utcnow()),
            updated_at=datetime.fromisoformat(data["updated_at"]) if isinstance(data.get("updated_at"), str) else data.get("updated_at", datetime.utcnow()),
        )


@dataclass
class KnowledgeQuery:
    """
    A search query for the knowledge retrieval system.

    Supports both text-based and semantic search with filtering options.

    Attributes:
        query_text: Text query for search
        query_embedding: Pre-computed embedding for semantic search
        base_id: Required - knowledge base to search within
        source_ids: Optional list of sources to filter by
        filters: Key-value filters to apply to metadata
        limit: Maximum number of results
        offset: Pagination offset
        min_score: Minimum relevance score threshold
        include_content: Whether to include content in results
        include_metadata: Whether to include metadata in results
    """

    base_id: str
    query_text: Optional[str] = None
    query_embedding: Optional[List[float]] = None
    source_ids: Optional[List[str]] = None
    filters: Dict[str, Any] = field(default_factory=dict)
    limit: int = 10
    offset: int = 0
    min_score: float = 0.0
    include_content: bool = True
    include_metadata: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "base_id": self.base_id,
            "query_text": self.query_text,
            "has_query_embedding": self.query_embedding is not None,
            "source_ids": self.source_ids,
            "filters": self.filters,
            "limit": self.limit,
            "offset": self.offset,
            "min_score": self.min_score,
            "include_content": self.include_content,
            "include_metadata": self.include_metadata,
        }


@dataclass
class RetrievalResult:
    """
    A single search result from knowledge retrieval.

    Contains the matched knowledge item along with relevance score
    and optional highlights.

    Attributes:
        item: The matched knowledge item
        score: Relevance score (0.0 to 1.0)
        highlights: Text snippets showing matches
        rank: Position in results (1-indexed)
    """

    item: KnowledgeItem
    score: float
    highlights: List[str] = field(default_factory=list)
    rank: int = 0

    def to_dict(self, include_embedding: bool = False) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "item_id": self.item.item_id,
            "source_id": self.item.source_id,
            "content": self.item.content,
            "title": self.item.title,
            "score": self.score,
            "rank": self.rank,
            "highlights": self.highlights,
            "metadata": self.item.metadata,
        }


@dataclass
class RetrievalResults:
    """
    Collection of retrieval results with metadata.

    Attributes:
        results: List of individual results
        total_count: Total number of matches (before pagination)
        query_time_ms: Time taken to execute query
        query: The original query
    """

    results: List[RetrievalResult] = field(default_factory=list)
    total_count: int = 0
    query_time_ms: float = 0.0
    query: Optional[KnowledgeQuery] = None

    @property
    def count(self) -> int:
        """Number of results returned."""
        return len(self.results)

    @property
    def has_results(self) -> bool:
        """Check if there are any results."""
        return len(self.results) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "results": [r.to_dict() for r in self.results],
            "count": self.count,
            "total_count": self.total_count,
            "query_time_ms": self.query_time_ms,
        }


@dataclass
class Citation:
    """
    A citation/attribution to a knowledge source.

    Used to ground answers in specific sources for transparency.

    Attributes:
        item_id: ID of the knowledge item cited
        source_id: ID of the source
        source_name: Human-readable source name
        content_excerpt: Excerpt from the cited content
        relevance_score: How relevant this citation is
        start_char: Start position of cited text
        end_char: End position of cited text
    """

    item_id: str
    source_id: str
    source_name: str
    content_excerpt: str
    relevance_score: float = 0.0
    start_char: Optional[int] = None
    end_char: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "item_id": self.item_id,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "content_excerpt": self.content_excerpt,
            "relevance_score": self.relevance_score,
            "start_char": self.start_char,
            "end_char": self.end_char,
        }


@dataclass
class GroundedAnswer:
    """
    An answer grounded in knowledge sources with citations.

    Represents a response generated from retrieved knowledge,
    including citations for transparency and verification.

    Attributes:
        answer_text: The generated answer text
        query: The original query
        citations: List of citations supporting the answer
        confidence_score: Model's confidence in the answer (0.0 to 1.0)
        base_id: Knowledge base used for retrieval
        retrieval_results: The underlying retrieval results
        generation_time_ms: Time to generate the answer
        model_name: Name of the model used for generation
        metadata: Additional metadata
    """

    answer_text: str
    query: str
    base_id: str
    citations: List[Citation] = field(default_factory=list)
    confidence_score: float = 0.0
    retrieval_results: Optional[RetrievalResults] = None
    generation_time_ms: float = 0.0
    model_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def citation_count(self) -> int:
        """Number of citations."""
        return len(self.citations)

    @property
    def is_grounded(self) -> bool:
        """Check if answer has citations."""
        return len(self.citations) > 0

    def to_dict(self, include_retrieval: bool = False) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "answer_text": self.answer_text,
            "query": self.query,
            "base_id": self.base_id,
            "citations": [c.to_dict() for c in self.citations],
            "citation_count": self.citation_count,
            "confidence_score": self.confidence_score,
            "is_grounded": self.is_grounded,
            "generation_time_ms": self.generation_time_ms,
            "model_name": self.model_name,
            "metadata": self.metadata,
        }
        if include_retrieval and self.retrieval_results:
            result["retrieval_results"] = self.retrieval_results.to_dict()
        return result
