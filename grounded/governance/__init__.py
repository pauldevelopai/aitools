"""
GROUNDED Governance - Policy, audit, and AI transparency framework.

Provides governance infrastructure including policy enforcement,
audit logging, AI operation tracking, and compliance for civic AI applications.

Usage:
    from grounded.governance import PolicyEngine, AuditLogger

    engine = PolicyEngine()
    engine.register_policy(MyPolicy())
    result = engine.evaluate("create_embedding", {"text": "..."})

    logger = AuditLogger()
    logger.log_event(AuditEvent(...))

AI Governance:
    from grounded.governance.ai import (
        AIGovernanceTracker,
        track_ai_operation,
        AIOperationType,
    )

    tracker = get_governance_tracker()
    stats = tracker.get_stats()
"""

from grounded.governance.policies.base import (
    BasePolicy,
    PolicyEngine,
    PolicyDecision,
    PolicyResult,
)
from grounded.governance.audit.logger import (
    AuditLogger,
    AuditEvent,
    AuditEventType,
)
from grounded.governance.ai import (
    AIOperationType,
    AIDataType,
    AIOperationStatus,
    AIAuditRecord,
    AIGovernanceStats,
    AIGovernanceTracker,
    get_governance_tracker,
    track_ai_operation,
    ai_operation_context,
    GovernedEmbeddingProvider,
)

__all__ = [
    # Policies
    "BasePolicy",
    "PolicyEngine",
    "PolicyDecision",
    "PolicyResult",
    # Audit
    "AuditLogger",
    "AuditEvent",
    "AuditEventType",
    # AI Governance
    "AIOperationType",
    "AIDataType",
    "AIOperationStatus",
    "AIAuditRecord",
    "AIGovernanceStats",
    "AIGovernanceTracker",
    "get_governance_tracker",
    "track_ai_operation",
    "ai_operation_context",
    "GovernedEmbeddingProvider",
]
