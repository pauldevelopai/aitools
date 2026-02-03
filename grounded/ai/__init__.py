"""
GROUNDED AI - AI processing abstractions and providers.

Provides protocol-based interfaces for AI capabilities including
embeddings and completions, with pluggable provider implementations.

Usage:
    from grounded.ai import get_embedding_provider, EmbeddingProvider

    provider = get_embedding_provider()
    embedding = provider.create_embedding("Hello, world!")
"""

from grounded.ai.providers.base import (
    EmbeddingProvider,
    CompletionProvider,
    BaseAIProvider,
)
from grounded.ai.providers.embedding import (
    OpenAIEmbeddingProvider,
    LocalStubEmbeddingProvider,
)
from grounded.core.base import Registry
from grounded.core.config import get_settings
from grounded.core.exceptions import ProviderNotFoundError

# Global registries for AI providers
embedding_registry: Registry[EmbeddingProvider] = Registry(name="embedding_providers")
completion_registry: Registry[CompletionProvider] = Registry(name="completion_providers")


def register_default_providers() -> None:
    """Register the default set of AI providers."""
    # Register local stub (always available)
    embedding_registry.register(
        "local_stub",
        LocalStubEmbeddingProvider(),
        set_as_default=True,
    )

    # Register OpenAI if API key is available
    settings = get_settings()
    if settings.openai_api_key:
        embedding_registry.register(
            "openai",
            OpenAIEmbeddingProvider(
                api_key=settings.openai_api_key,
                model=settings.openai_embedding_model,
            ),
        )


def get_embedding_provider(key: str | None = None) -> EmbeddingProvider:
    """
    Get an embedding provider by key or return the default.

    Args:
        key: Optional provider key. If None, returns the default provider.

    Returns:
        EmbeddingProvider instance

    Raises:
        ProviderNotFoundError: If provider not found
    """
    if key is None:
        provider = embedding_registry.get_default()
        if provider is None:
            raise ProviderNotFoundError(
                provider_type="embedding",
                provider_key="default",
                available_providers=embedding_registry.list_keys(),
            )
        return provider

    provider = embedding_registry.get(key)
    if provider is None:
        raise ProviderNotFoundError(
            provider_type="embedding",
            provider_key=key,
            available_providers=embedding_registry.list_keys(),
        )
    return provider


def get_completion_provider(key: str | None = None) -> CompletionProvider:
    """
    Get a completion provider by key or return the default.

    Args:
        key: Optional provider key. If None, returns the default provider.

    Returns:
        CompletionProvider instance

    Raises:
        ProviderNotFoundError: If provider not found
    """
    if key is None:
        provider = completion_registry.get_default()
        if provider is None:
            raise ProviderNotFoundError(
                provider_type="completion",
                provider_key="default",
                available_providers=completion_registry.list_keys(),
            )
        return provider

    provider = completion_registry.get(key)
    if provider is None:
        raise ProviderNotFoundError(
            provider_type="completion",
            provider_key=key,
            available_providers=completion_registry.list_keys(),
        )
    return provider


__all__ = [
    # Protocols
    "EmbeddingProvider",
    "CompletionProvider",
    "BaseAIProvider",
    # Implementations
    "OpenAIEmbeddingProvider",
    "LocalStubEmbeddingProvider",
    # Registries
    "embedding_registry",
    "completion_registry",
    # Helper functions
    "get_embedding_provider",
    "get_completion_provider",
    "register_default_providers",
]
