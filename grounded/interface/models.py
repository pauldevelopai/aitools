"""
GROUNDED Interface Models - Request/response models for the interface API.

Defines structured data models for all interface operations, enabling
type-safe communication between GROUNDED and external civic tools.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class InterfaceVersion(Enum):
    """Interface API versions."""

    V1 = "v1"


class CapabilityType(Enum):
    """Types of capabilities exposed by GROUNDED."""

    # AI Processing
    EMBEDDING = "embedding"
    EMBEDDING_BATCH = "embedding_batch"
    COMPLETION = "completion"  # Future

    # Knowledge System
    KNOWLEDGE_BASE_MANAGE = "knowledge_base_manage"
    KNOWLEDGE_SEARCH = "knowledge_search"
    KNOWLEDGE_ANSWER = "knowledge_answer"

    # Document Processing
    DOCUMENT_PROCESS = "document_process"
    DOCUMENT_CHUNK = "document_chunk"

    # Governance
    GOVERNANCE_STATS = "governance_stats"
    GOVERNANCE_AUDIT = "governance_audit"

    # System
    HEALTH_CHECK = "health_check"
    CAPABILITY_LIST = "capability_list"


class RequestStatus(Enum):
    """Status of an interface request."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    UNAUTHORIZED = "unauthorized"


# =============================================================================
# BASE REQUEST/RESPONSE
# =============================================================================


@dataclass
class InterfaceRequest:
    """
    Base class for all interface requests.

    All requests to the GROUNDED interface include client identification
    and tracking metadata.
    """

    client_id: str
    capability: CapabilityType = CapabilityType.HEALTH_CHECK  # Default, overridden by subclasses
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    api_version: InterfaceVersion = InterfaceVersion.V1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "request_id": self.request_id,
            "client_id": self.client_id,
            "capability": self.capability.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "api_version": self.api_version.value,
        }


@dataclass
class InterfaceResponse:
    """
    Base class for all interface responses.

    All responses include the original request ID for correlation
    and status information.
    """

    request_id: str
    status: RequestStatus
    timestamp: datetime = field(default_factory=datetime.utcnow)
    processing_time_ms: float = 0.0
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        """Check if the response indicates success."""
        return self.status == RequestStatus.COMPLETED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "request_id": self.request_id,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "processing_time_ms": self.processing_time_ms,
            "error_message": self.error_message,
            "error_code": self.error_code,
            "metadata": self.metadata,
            "success": self.is_success,
        }


# =============================================================================
# AI PROCESSING REQUESTS/RESPONSES
# =============================================================================


@dataclass
class EmbeddingRequest(InterfaceRequest):
    """Request to generate an embedding for text."""

    text: str = ""

    def __post_init__(self):
        self.capability = CapabilityType.EMBEDDING


@dataclass
class EmbeddingResponse(InterfaceResponse):
    """Response containing an embedding vector."""

    embedding: Optional[List[float]] = None
    dimensions: int = 0
    provider: str = ""
    model: str = ""

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            "embedding": self.embedding,
            "dimensions": self.dimensions,
            "provider": self.provider,
            "model": self.model,
        })
        return result


@dataclass
class BatchEmbeddingRequest(InterfaceRequest):
    """Request to generate embeddings for multiple texts."""

    texts: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.capability = CapabilityType.EMBEDDING_BATCH


@dataclass
class BatchEmbeddingResponse(InterfaceResponse):
    """Response containing multiple embedding vectors."""

    embeddings: List[List[float]] = field(default_factory=list)
    count: int = 0
    dimensions: int = 0
    provider: str = ""
    model: str = ""

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            "embeddings": self.embeddings,
            "count": self.count,
            "dimensions": self.dimensions,
            "provider": self.provider,
            "model": self.model,
        })
        return result


# =============================================================================
# KNOWLEDGE SYSTEM REQUESTS/RESPONSES
# =============================================================================


@dataclass
class CreateKnowledgeBaseRequest(InterfaceRequest):
    """Request to create a new knowledge base."""

    name: str = ""
    description: str = ""
    owner_type: str = "client"
    owner_id: str = ""
    kb_metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.capability = CapabilityType.KNOWLEDGE_BASE_MANAGE
        if not self.owner_id:
            self.owner_id = self.client_id


@dataclass
class CreateKnowledgeBaseResponse(InterfaceResponse):
    """Response containing created knowledge base info."""

    base_id: Optional[str] = None
    name: str = ""
    owner_type: str = ""
    owner_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            "base_id": self.base_id,
            "name": self.name,
            "owner_type": self.owner_type,
            "owner_id": self.owner_id,
        })
        return result


@dataclass
class AddKnowledgeRequest(InterfaceRequest):
    """Request to add knowledge to a base."""

    base_id: str = ""
    source_name: str = ""
    content: str = ""
    title: Optional[str] = None
    content_metadata: Dict[str, Any] = field(default_factory=dict)
    generate_embedding: bool = True

    def __post_init__(self):
        self.capability = CapabilityType.KNOWLEDGE_BASE_MANAGE


@dataclass
class AddKnowledgeResponse(InterfaceResponse):
    """Response from adding knowledge."""

    item_id: Optional[str] = None
    source_id: Optional[str] = None
    has_embedding: bool = False

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            "item_id": self.item_id,
            "source_id": self.source_id,
            "has_embedding": self.has_embedding,
        })
        return result


@dataclass
class KnowledgeSearchRequest(InterfaceRequest):
    """Request to search a knowledge base."""

    base_id: str = ""
    query: str = ""
    limit: int = 10
    source_ids: Optional[List[str]] = None
    filters: Dict[str, Any] = field(default_factory=dict)
    search_type: str = "hybrid"  # "text", "semantic", or "hybrid"
    min_score: float = 0.0

    def __post_init__(self):
        self.capability = CapabilityType.KNOWLEDGE_SEARCH


@dataclass
class SearchResultItem:
    """A single search result."""

    item_id: str
    source_id: str
    content: str
    title: Optional[str]
    score: float
    rank: int
    highlights: List[str] = field(default_factory=list)
    item_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "source_id": self.source_id,
            "content": self.content,
            "title": self.title,
            "score": self.score,
            "rank": self.rank,
            "highlights": self.highlights,
            "metadata": self.item_metadata,
        }


@dataclass
class KnowledgeSearchResponse(InterfaceResponse):
    """Response containing search results."""

    results: List[SearchResultItem] = field(default_factory=list)
    total_count: int = 0
    query_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            "results": [r.to_dict() for r in self.results],
            "total_count": self.total_count,
            "result_count": len(self.results),
            "query_time_ms": self.query_time_ms,
        })
        return result


@dataclass
class KnowledgeAnswerRequest(InterfaceRequest):
    """Request for a grounded answer."""

    base_id: str = ""
    question: str = ""
    limit: int = 5
    source_ids: Optional[List[str]] = None
    context: Optional[str] = None

    def __post_init__(self):
        self.capability = CapabilityType.KNOWLEDGE_ANSWER


@dataclass
class CitationItem:
    """A citation/source for an answer."""

    item_id: str
    source_id: str
    source_name: str
    excerpt: str
    relevance_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "excerpt": self.excerpt,
            "relevance_score": self.relevance_score,
        }


@dataclass
class KnowledgeAnswerResponse(InterfaceResponse):
    """Response containing a grounded answer."""

    answer: str = ""
    citations: List[CitationItem] = field(default_factory=list)
    confidence_score: float = 0.0
    is_grounded: bool = False

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            "answer": self.answer,
            "citations": [c.to_dict() for c in self.citations],
            "citation_count": len(self.citations),
            "confidence_score": self.confidence_score,
            "is_grounded": self.is_grounded,
        })
        return result


# =============================================================================
# DOCUMENT PROCESSING REQUESTS/RESPONSES
# =============================================================================


@dataclass
class ProcessDocumentRequest(InterfaceRequest):
    """Request to process a document."""

    content: str = ""
    title: Optional[str] = None
    document_type: str = "text"  # "text", "markdown"
    chunking_strategy: str = "sentence"
    chunk_size: int = 500
    generate_embeddings: bool = True

    def __post_init__(self):
        self.capability = CapabilityType.DOCUMENT_PROCESS


@dataclass
class ChunkInfo:
    """Information about a document chunk."""

    chunk_id: str
    index: int
    content: str
    char_count: int
    word_count: int
    has_embedding: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "index": self.index,
            "content": self.content,
            "char_count": self.char_count,
            "word_count": self.word_count,
            "has_embedding": self.has_embedding,
        }


@dataclass
class ProcessDocumentResponse(InterfaceResponse):
    """Response from document processing."""

    document_id: Optional[str] = None
    chunk_count: int = 0
    embedding_count: int = 0
    chunks: List[ChunkInfo] = field(default_factory=list)
    document_word_count: int = 0
    document_char_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            "document_id": self.document_id,
            "chunk_count": self.chunk_count,
            "embedding_count": self.embedding_count,
            "chunks": [c.to_dict() for c in self.chunks],
            "document_word_count": self.document_word_count,
            "document_char_count": self.document_char_count,
        })
        return result


# =============================================================================
# GOVERNANCE REQUESTS/RESPONSES
# =============================================================================


@dataclass
class GovernanceStatsRequest(InterfaceRequest):
    """Request for governance statistics."""

    include_by_type: bool = True
    include_by_provider: bool = True
    time_range_hours: Optional[int] = None

    def __post_init__(self):
        self.capability = CapabilityType.GOVERNANCE_STATS


@dataclass
class GovernanceStatsResponse(InterfaceResponse):
    """Response containing governance statistics."""

    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    success_rate: float = 0.0
    total_tokens: int = 0
    avg_duration_ms: float = 0.0
    operations_by_type: Dict[str, int] = field(default_factory=dict)
    operations_by_provider: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            "total_operations": self.total_operations,
            "successful_operations": self.successful_operations,
            "failed_operations": self.failed_operations,
            "success_rate": self.success_rate,
            "total_tokens": self.total_tokens,
            "avg_duration_ms": self.avg_duration_ms,
            "operations_by_type": self.operations_by_type,
            "operations_by_provider": self.operations_by_provider,
        })
        return result


# =============================================================================
# SYSTEM REQUESTS/RESPONSES
# =============================================================================


@dataclass
class HealthCheckRequest(InterfaceRequest):
    """Request for system health check."""

    include_components: bool = True

    def __post_init__(self):
        self.capability = CapabilityType.HEALTH_CHECK


@dataclass
class ComponentHealth:
    """Health status of a component."""

    name: str
    status: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "details": self.details,
        }


@dataclass
class HealthCheckResponse(InterfaceResponse):
    """Response containing health information."""

    overall_status: str = "healthy"
    version: str = ""
    components: List[ComponentHealth] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            "overall_status": self.overall_status,
            "version": self.version,
            "components": [c.to_dict() for c in self.components],
        })
        return result


@dataclass
class CapabilityListRequest(InterfaceRequest):
    """Request for available capabilities."""

    def __post_init__(self):
        self.capability = CapabilityType.CAPABILITY_LIST


@dataclass
class CapabilityInfo:
    """Information about a capability."""

    capability: CapabilityType
    name: str
    description: str
    enabled: bool
    requires_auth: bool
    rate_limit: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capability": self.capability.value,
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "requires_auth": self.requires_auth,
            "rate_limit": self.rate_limit,
        }


@dataclass
class CapabilityListResponse(InterfaceResponse):
    """Response containing available capabilities."""

    capabilities: List[CapabilityInfo] = field(default_factory=list)
    api_version: str = "v1"

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            "capabilities": [c.to_dict() for c in self.capabilities],
            "api_version": self.api_version,
            "capability_count": len(self.capabilities),
        })
        return result
