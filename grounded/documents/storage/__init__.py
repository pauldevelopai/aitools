"""
GROUNDED Document Storage - Storage backends for processed documents.

Provides protocol-based storage abstraction with pluggable backends
for persisting processed documents and their embeddings.
"""

from grounded.documents.storage.base import (
    BaseDocumentStorage,
    DocumentStorageProtocol,
    SearchResult,
    SearchResults,
    SearchQuery,
)
from grounded.documents.storage.memory import InMemoryDocumentStorage
from grounded.core.base import Registry

# Global storage registry
storage_registry: Registry[BaseDocumentStorage] = Registry(name="document_storage")


def register_default_storage() -> None:
    """Register the default storage backend."""
    storage_registry.register("memory", InMemoryDocumentStorage(), set_as_default=True)


def get_storage(backend: str = "memory") -> BaseDocumentStorage:
    """
    Get a storage backend by name.

    Args:
        backend: Storage backend name

    Returns:
        Storage backend instance
    """
    return storage_registry.get_or_raise(backend)


__all__ = [
    "BaseDocumentStorage",
    "DocumentStorageProtocol",
    "SearchResult",
    "SearchResults",
    "SearchQuery",
    "InMemoryDocumentStorage",
    "storage_registry",
    "register_default_storage",
    "get_storage",
]
