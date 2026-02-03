"""
GROUNDED AI Providers - AI provider implementations.

Contains protocol definitions and concrete implementations for
various AI capabilities including embeddings and completions.
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

__all__ = [
    "EmbeddingProvider",
    "CompletionProvider",
    "BaseAIProvider",
    "OpenAIEmbeddingProvider",
    "LocalStubEmbeddingProvider",
]
