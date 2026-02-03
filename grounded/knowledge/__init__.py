"""
GROUNDED Knowledge - Multi-tenant knowledge infrastructure for AI applications.

Provides knowledge management, semantic search, and grounded answer generation
with source citations.

Usage:
    from grounded.knowledge import KnowledgeService

    # Initialize
    service = KnowledgeService()
    await service.initialize()

    # Create knowledge base for an organization
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
    print(answer.answer_text)
    print(answer.citations)
"""

# Models
from grounded.knowledge.models import (
    KnowledgeBase,
    KnowledgeBaseStatus,
    KnowledgeSource,
    KnowledgeSourceType,
    KnowledgeItem,
    KnowledgeItemStatus,
    KnowledgeQuery,
    RetrievalResult,
    RetrievalResults,
    Citation,
    GroundedAnswer,
)

# Exceptions
from grounded.knowledge.exceptions import (
    KnowledgeError,
    KnowledgeBaseNotFoundError,
    KnowledgeSourceNotFoundError,
    KnowledgeItemNotFoundError,
    DuplicateKnowledgeBaseError,
    DuplicateKnowledgeSourceError,
    TenantIsolationError,
    EmbeddingError,
    RetrievalError,
    AnswerGenerationError,
    StorageError,
)

# Core components
from grounded.knowledge.repository import KnowledgeRepository
from grounded.knowledge.retriever import KnowledgeRetriever
from grounded.knowledge.answerer import KnowledgeAnswerer
from grounded.knowledge.service import KnowledgeService

# Storage
from grounded.knowledge.storage import (
    BaseKnowledgeStorage,
    InMemoryKnowledgeStorage,
    get_storage,
    register_storage,
)

__all__ = [
    # Main service
    "KnowledgeService",
    # Models
    "KnowledgeBase",
    "KnowledgeBaseStatus",
    "KnowledgeSource",
    "KnowledgeSourceType",
    "KnowledgeItem",
    "KnowledgeItemStatus",
    "KnowledgeQuery",
    "RetrievalResult",
    "RetrievalResults",
    "Citation",
    "GroundedAnswer",
    # Exceptions
    "KnowledgeError",
    "KnowledgeBaseNotFoundError",
    "KnowledgeSourceNotFoundError",
    "KnowledgeItemNotFoundError",
    "DuplicateKnowledgeBaseError",
    "DuplicateKnowledgeSourceError",
    "TenantIsolationError",
    "EmbeddingError",
    "RetrievalError",
    "AnswerGenerationError",
    "StorageError",
    # Core components
    "KnowledgeRepository",
    "KnowledgeRetriever",
    "KnowledgeAnswerer",
    # Storage
    "BaseKnowledgeStorage",
    "InMemoryKnowledgeStorage",
    "get_storage",
    "register_storage",
]
