"""
GROUNDED AI Governance - Cross-cutting AI transparency and accountability layer.

Provides automatic tracking and auditing of all AI operations across the
GROUNDED infrastructure. This governance layer sits underneath AI processes
and records what happens whenever AI is used.

Key Features:
- Automatic tracking of AI operations (embeddings, completions, document processing)
- Structured audit records with operation context
- Non-intrusive integration via decorators and context managers
- Queryable audit trail for transparency and compliance

Usage:
    # Using the decorator
    from grounded.governance.ai import track_ai_operation, AIOperationType

    @track_ai_operation(AIOperationType.EMBEDDING)
    def create_embedding(text: str) -> List[float]:
        ...

    # Using the context manager
    from grounded.governance.ai import ai_operation_context

    with ai_operation_context(AIOperationType.COMPLETION, source="chatbot") as ctx:
        result = provider.complete(prompt)
        ctx.record_output(tokens=100)

    # Using governed providers (auto-tracking)
    from grounded.governance.ai import GovernedEmbeddingProvider

    provider = GovernedEmbeddingProvider(base_provider)
    embedding = provider.create_embedding("text")  # Automatically tracked
"""

from grounded.governance.ai.models import (
    AIOperationType,
    AIDataType,
    AIOperationStatus,
    AIOperationContext,
    AIAuditRecord,
    AIGovernanceStats,
)
from grounded.governance.ai.tracker import (
    AIGovernanceTracker,
    get_governance_tracker,
    set_governance_tracker,
)
from grounded.governance.ai.integration import (
    track_ai_operation,
    ai_operation_context,
    AIOperationContextManager,
)
from grounded.governance.ai.providers import (
    GovernedEmbeddingProvider,
    wrap_embedding_provider,
)

__all__ = [
    # Models
    "AIOperationType",
    "AIDataType",
    "AIOperationStatus",
    "AIOperationContext",
    "AIAuditRecord",
    "AIGovernanceStats",
    # Tracker
    "AIGovernanceTracker",
    "get_governance_tracker",
    "set_governance_tracker",
    # Integration
    "track_ai_operation",
    "ai_operation_context",
    "AIOperationContextManager",
    # Providers
    "GovernedEmbeddingProvider",
    "wrap_embedding_provider",
]
