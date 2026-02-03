"""
GROUNDED AI Governance Models - Data structures for AI audit tracking.

Defines the core data models for tracking AI operations:
- Operation types (what kind of AI task)
- Data types (what kind of data was involved)
- Operation context (who triggered it, from where)
- Audit records (complete audit trail)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class AIOperationType(Enum):
    """Types of AI operations that can be tracked."""

    # Embedding operations
    EMBEDDING = "embedding"
    EMBEDDING_BATCH = "embedding_batch"

    # Completion/generation operations
    COMPLETION = "completion"
    CHAT_COMPLETION = "chat_completion"
    STREAMING_COMPLETION = "streaming_completion"

    # Document operations
    DOCUMENT_EXTRACTION = "document_extraction"
    DOCUMENT_CHUNKING = "document_chunking"
    DOCUMENT_PROCESSING = "document_processing"

    # Search operations
    SEMANTIC_SEARCH = "semantic_search"
    SIMILARITY_SEARCH = "similarity_search"

    # Knowledge operations
    KNOWLEDGE_SEARCH = "knowledge_search"
    KNOWLEDGE_ANSWER = "knowledge_answer"

    # Analysis operations
    CLASSIFICATION = "classification"
    SUMMARIZATION = "summarization"
    ENTITY_EXTRACTION = "entity_extraction"

    # Generic
    CUSTOM = "custom"


class AIDataType(Enum):
    """Types of data involved in AI operations."""

    TEXT = "text"
    DOCUMENT = "document"
    IMAGE = "image"
    AUDIO = "audio"
    EMBEDDING_VECTOR = "embedding_vector"
    STRUCTURED_DATA = "structured_data"
    USER_CONTENT = "user_content"
    SYSTEM_CONTENT = "system_content"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class AIOperationStatus(Enum):
    """Status of an AI operation."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AIOperationContext:
    """
    Context information about an AI operation.

    Captures metadata about who triggered the operation, from where,
    and what data was involved.
    """

    # Operation identification
    operation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    operation_type: AIOperationType = AIOperationType.CUSTOM

    # Source information (where the operation was triggered)
    source_module: str = ""  # e.g., "grounded.documents.processor"
    source_function: str = ""  # e.g., "process_document"
    source_component: str = ""  # e.g., "DocumentProcessor"

    # Actor information (who/what triggered it)
    actor_type: str = "system"  # "system", "user", "api", "scheduled"
    actor_id: Optional[str] = None  # User ID, API key ID, etc.
    session_id: Optional[str] = None

    # Data information
    input_data_type: AIDataType = AIDataType.UNKNOWN
    input_size: int = 0  # Size in bytes/chars/tokens as appropriate
    input_count: int = 1  # Number of items (e.g., batch size)

    # Provider information
    provider_name: str = ""  # e.g., "openai", "local_stub"
    model_name: str = ""  # e.g., "text-embedding-3-small"

    # Additional metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Correlation for tracking related operations
    correlation_id: Optional[str] = None
    parent_operation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type.value,
            "source_module": self.source_module,
            "source_function": self.source_function,
            "source_component": self.source_component,
            "actor_type": self.actor_type,
            "actor_id": self.actor_id,
            "session_id": self.session_id,
            "input_data_type": self.input_data_type.value,
            "input_size": self.input_size,
            "input_count": self.input_count,
            "provider_name": self.provider_name,
            "model_name": self.model_name,
            "tags": self.tags,
            "metadata": self.metadata,
            "correlation_id": self.correlation_id,
            "parent_operation_id": self.parent_operation_id,
        }


@dataclass
class AIAuditRecord:
    """
    Complete audit record for an AI operation.

    This is the primary record stored in the audit trail, containing
    both the operation context and the results/metrics.
    """

    # Context
    context: AIOperationContext

    # Timing
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Status
    status: AIOperationStatus = AIOperationStatus.PENDING

    # Output information
    output_data_type: AIDataType = AIDataType.UNKNOWN
    output_size: int = 0
    output_count: int = 0

    # Metrics
    duration_ms: float = 0.0
    tokens_input: int = 0
    tokens_output: int = 0
    tokens_total: int = 0

    # Cost tracking (optional)
    estimated_cost_usd: float = 0.0

    # Error information
    error_message: Optional[str] = None
    error_type: Optional[str] = None

    # Additional results
    result_metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def record_id(self) -> str:
        """Unique identifier for this record."""
        return self.context.operation_id

    @property
    def operation_type(self) -> AIOperationType:
        """Convenience accessor for operation type."""
        return self.context.operation_type

    @property
    def is_complete(self) -> bool:
        """Check if the operation has completed."""
        return self.status in (
            AIOperationStatus.COMPLETED,
            AIOperationStatus.FAILED,
            AIOperationStatus.CANCELLED,
        )

    @property
    def is_success(self) -> bool:
        """Check if the operation completed successfully."""
        return self.status == AIOperationStatus.COMPLETED

    def complete(
        self,
        output_size: int = 0,
        output_count: int = 0,
        tokens_output: int = 0,
        **result_metadata: Any,
    ) -> None:
        """Mark the operation as completed successfully."""
        self.completed_at = datetime.utcnow()
        self.status = AIOperationStatus.COMPLETED
        self.output_size = output_size
        self.output_count = output_count
        self.tokens_output = tokens_output
        self.tokens_total = self.tokens_input + tokens_output
        self.duration_ms = (self.completed_at - self.started_at).total_seconds() * 1000
        self.result_metadata.update(result_metadata)

    def fail(self, error_message: str, error_type: Optional[str] = None) -> None:
        """Mark the operation as failed."""
        self.completed_at = datetime.utcnow()
        self.status = AIOperationStatus.FAILED
        self.error_message = error_message
        self.error_type = error_type or "unknown"
        self.duration_ms = (self.completed_at - self.started_at).total_seconds() * 1000

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "record_id": self.record_id,
            "context": self.context.to_dict(),
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status.value,
            "output_data_type": self.output_data_type.value,
            "output_size": self.output_size,
            "output_count": self.output_count,
            "duration_ms": self.duration_ms,
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "tokens_total": self.tokens_total,
            "estimated_cost_usd": self.estimated_cost_usd,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "result_metadata": self.result_metadata,
        }

    def to_log_string(self) -> str:
        """Create a log-friendly string representation."""
        status_emoji = "✓" if self.is_success else "✗" if self.status == AIOperationStatus.FAILED else "○"
        return (
            f"{status_emoji} [{self.operation_type.value}] "
            f"provider={self.context.provider_name} "
            f"duration={self.duration_ms:.1f}ms "
            f"source={self.context.source_component or self.context.source_module}"
        )


@dataclass
class AIGovernanceStats:
    """
    Aggregated statistics from AI governance tracking.

    Provides summary metrics for monitoring and reporting.
    """

    # Counts
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0

    # By type
    operations_by_type: Dict[str, int] = field(default_factory=dict)

    # By provider
    operations_by_provider: Dict[str, int] = field(default_factory=dict)

    # By source
    operations_by_source: Dict[str, int] = field(default_factory=dict)

    # Timing
    total_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0
    min_duration_ms: float = 0.0
    max_duration_ms: float = 0.0

    # Tokens
    total_tokens: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0

    # Cost
    total_estimated_cost_usd: float = 0.0

    # Time range
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_operations == 0:
            return 0.0
        return (self.successful_operations / self.total_operations) * 100

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate as percentage."""
        if self.total_operations == 0:
            return 0.0
        return (self.failed_operations / self.total_operations) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "total_operations": self.total_operations,
            "successful_operations": self.successful_operations,
            "failed_operations": self.failed_operations,
            "success_rate": self.success_rate,
            "failure_rate": self.failure_rate,
            "operations_by_type": self.operations_by_type,
            "operations_by_provider": self.operations_by_provider,
            "operations_by_source": self.operations_by_source,
            "total_duration_ms": self.total_duration_ms,
            "avg_duration_ms": self.avg_duration_ms,
            "min_duration_ms": self.min_duration_ms,
            "max_duration_ms": self.max_duration_ms,
            "total_tokens": self.total_tokens,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_estimated_cost_usd": self.total_estimated_cost_usd,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
        }
