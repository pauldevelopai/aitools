"""
GROUNDED Knowledge Storage - Pluggable storage backends for knowledge management.

Provides the storage abstraction layer for knowledge bases, sources, and items.
Supports multiple backend implementations with a registry pattern.

Usage:
    from grounded.knowledge.storage import get_storage, InMemoryKnowledgeStorage

    # Get default storage
    storage = get_storage()

    # Or get specific backend
    storage = get_storage("in_memory")

    # Or create directly
    storage = InMemoryKnowledgeStorage()
"""

from typing import Optional

from grounded.core.base import Registry
from grounded.core.exceptions import ProviderNotFoundError
from grounded.knowledge.storage.base import (
    BaseKnowledgeStorage,
    KnowledgeStorageProtocol,
)
from grounded.knowledge.storage.memory import InMemoryKnowledgeStorage

# Global registry for knowledge storage backends
storage_registry: Registry[BaseKnowledgeStorage] = Registry(name="knowledge_storage")


def register_default_storage() -> None:
    """Register the default set of storage backends."""
    storage_registry.register(
        "in_memory",
        InMemoryKnowledgeStorage(),
        set_as_default=True,
    )


def get_storage(key: Optional[str] = None) -> BaseKnowledgeStorage:
    """
    Get a knowledge storage backend by key or return the default.

    Args:
        key: Optional storage backend key. If None, returns the default.

    Returns:
        BaseKnowledgeStorage instance

    Raises:
        ProviderNotFoundError: If storage backend not found
    """
    if key is None:
        storage = storage_registry.get_default()
        if storage is None:
            # Auto-register defaults if not done yet
            register_default_storage()
            storage = storage_registry.get_default()
        if storage is None:
            raise ProviderNotFoundError(
                provider_type="knowledge_storage",
                provider_key="default",
                available_providers=storage_registry.list_keys(),
            )
        return storage

    storage = storage_registry.get(key)
    if storage is None:
        raise ProviderNotFoundError(
            provider_type="knowledge_storage",
            provider_key=key,
            available_providers=storage_registry.list_keys(),
        )
    return storage


def register_storage(
    key: str,
    storage: BaseKnowledgeStorage,
    set_as_default: bool = False,
) -> None:
    """
    Register a knowledge storage backend.

    Args:
        key: Unique key for the storage backend
        storage: The storage backend instance
        set_as_default: Whether to set as the default backend
    """
    storage_registry.register(key, storage, set_as_default=set_as_default)


__all__ = [
    # Base classes
    "BaseKnowledgeStorage",
    "KnowledgeStorageProtocol",
    # Implementations
    "InMemoryKnowledgeStorage",
    # Registry
    "storage_registry",
    # Helper functions
    "get_storage",
    "register_storage",
    "register_default_storage",
]
