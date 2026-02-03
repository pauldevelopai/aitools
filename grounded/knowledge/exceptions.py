"""
GROUNDED Knowledge Exceptions - Custom exception hierarchy for knowledge operations.

Provides knowledge-specific exceptions for clear error handling
in the knowledge and retrieval subsystem.
"""

from typing import Any, Dict, List, Optional

from grounded.core.exceptions import GroundedException


class KnowledgeError(GroundedException):
    """
    Base exception for all knowledge-related errors.

    All knowledge-specific exceptions should inherit from this class
    to allow for consistent error handling.
    """

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code=code or "KNOWLEDGE_ERROR",
            details=details or {},
        )


class KnowledgeBaseNotFoundError(KnowledgeError):
    """
    Raised when a knowledge base is not found.

    Example:
        raise KnowledgeBaseNotFoundError(base_id="kb-123")
    """

    def __init__(self, base_id: str):
        self.base_id = base_id
        super().__init__(
            message=f"Knowledge base '{base_id}' not found",
            code="KNOWLEDGE_BASE_NOT_FOUND",
            details={"base_id": base_id},
        )


class KnowledgeSourceNotFoundError(KnowledgeError):
    """
    Raised when a knowledge source is not found.

    Example:
        raise KnowledgeSourceNotFoundError(source_id="src-123", base_id="kb-456")
    """

    def __init__(self, source_id: str, base_id: Optional[str] = None):
        self.source_id = source_id
        self.base_id = base_id

        message = f"Knowledge source '{source_id}' not found"
        if base_id:
            message += f" in base '{base_id}'"

        super().__init__(
            message=message,
            code="KNOWLEDGE_SOURCE_NOT_FOUND",
            details={"source_id": source_id, "base_id": base_id},
        )


class KnowledgeItemNotFoundError(KnowledgeError):
    """
    Raised when a knowledge item is not found.

    Example:
        raise KnowledgeItemNotFoundError(item_id="item-123")
    """

    def __init__(self, item_id: str, source_id: Optional[str] = None):
        self.item_id = item_id
        self.source_id = source_id

        message = f"Knowledge item '{item_id}' not found"
        if source_id:
            message += f" in source '{source_id}'"

        super().__init__(
            message=message,
            code="KNOWLEDGE_ITEM_NOT_FOUND",
            details={"item_id": item_id, "source_id": source_id},
        )


class DuplicateKnowledgeBaseError(KnowledgeError):
    """
    Raised when attempting to create a duplicate knowledge base.

    Example:
        raise DuplicateKnowledgeBaseError(base_id="kb-123")
    """

    def __init__(self, base_id: str):
        self.base_id = base_id
        super().__init__(
            message=f"Knowledge base '{base_id}' already exists",
            code="DUPLICATE_KNOWLEDGE_BASE",
            details={"base_id": base_id},
        )


class DuplicateKnowledgeSourceError(KnowledgeError):
    """
    Raised when attempting to create a duplicate knowledge source.

    Example:
        raise DuplicateKnowledgeSourceError(source_id="src-123", base_id="kb-456")
    """

    def __init__(self, source_id: str, base_id: str):
        self.source_id = source_id
        self.base_id = base_id
        super().__init__(
            message=f"Knowledge source '{source_id}' already exists in base '{base_id}'",
            code="DUPLICATE_KNOWLEDGE_SOURCE",
            details={"source_id": source_id, "base_id": base_id},
        )


class TenantIsolationError(KnowledgeError):
    """
    Raised when a tenant isolation boundary is violated.

    Example:
        raise TenantIsolationError(
            message="Cannot access source from different knowledge base",
            base_id="kb-123",
            requested_resource="src-456"
        )
    """

    def __init__(
        self,
        message: str,
        base_id: str,
        requested_resource: Optional[str] = None,
    ):
        self.base_id = base_id
        self.requested_resource = requested_resource
        super().__init__(
            message=message,
            code="TENANT_ISOLATION_VIOLATION",
            details={
                "base_id": base_id,
                "requested_resource": requested_resource,
            },
        )


class EmbeddingError(KnowledgeError):
    """
    Raised when there is an error generating embeddings.

    Example:
        raise EmbeddingError(
            message="Failed to generate embedding for text",
            provider="openai",
            original_error=e
        )
    """

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        self.provider = provider
        self.original_error = original_error
        super().__init__(
            message=message,
            code="EMBEDDING_ERROR",
            details={
                "provider": provider,
                "original_error": str(original_error) if original_error else None,
            },
        )


class RetrievalError(KnowledgeError):
    """
    Raised when there is an error during retrieval operations.

    Example:
        raise RetrievalError(
            message="Search failed due to storage error",
            query="vacation days",
            original_error=e
        )
    """

    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        self.query = query
        self.original_error = original_error
        super().__init__(
            message=message,
            code="RETRIEVAL_ERROR",
            details={
                "query": query,
                "original_error": str(original_error) if original_error else None,
            },
        )


class AnswerGenerationError(KnowledgeError):
    """
    Raised when there is an error generating an answer.

    Example:
        raise AnswerGenerationError(
            message="Failed to generate grounded answer",
            query="How many vacation days?",
            original_error=e
        )
    """

    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        self.query = query
        self.original_error = original_error
        super().__init__(
            message=message,
            code="ANSWER_GENERATION_ERROR",
            details={
                "query": query,
                "original_error": str(original_error) if original_error else None,
            },
        )


class StorageError(KnowledgeError):
    """
    Raised when there is a storage-related error.

    Example:
        raise StorageError(
            message="Failed to persist knowledge item",
            operation="store_item",
            original_error=e
        )
    """

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        self.operation = operation
        self.original_error = original_error
        super().__init__(
            message=message,
            code="KNOWLEDGE_STORAGE_ERROR",
            details={
                "operation": operation,
                "original_error": str(original_error) if original_error else None,
            },
        )
