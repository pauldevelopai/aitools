"""
GROUNDED AI Provider Base - Protocol definitions for AI providers.

Defines the interfaces (protocols) that AI providers must implement,
enabling pluggable AI capabilities throughout the GROUNDED infrastructure.
"""

from abc import abstractmethod
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from grounded.core.base import GroundedComponent


@runtime_checkable
class EmbeddingProvider(Protocol):
    """
    Protocol for embedding providers.

    Any class implementing this protocol can be used as an embedding provider
    in the GROUNDED infrastructure.

    Example:
        class MyEmbeddingProvider:
            @property
            def name(self) -> str:
                return "my_provider"

            @property
            def dimensions(self) -> int:
                return 768

            def create_embedding(self, text: str) -> List[float]:
                # Your embedding logic here
                return [0.0] * 768

            def create_embeddings(self, texts: List[str]) -> List[List[float]]:
                return [self.create_embedding(t) for t in texts]
    """

    @property
    def name(self) -> str:
        """Provider name identifier."""
        ...

    @property
    def dimensions(self) -> int:
        """Embedding vector dimensions."""
        ...

    def create_embedding(self, text: str) -> List[float]:
        """
        Create an embedding for a single text.

        Args:
            text: The text to embed

        Returns:
            List of floats representing the embedding vector
        """
        ...

    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Create embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        ...


@runtime_checkable
class CompletionProvider(Protocol):
    """
    Protocol for completion (text generation) providers.

    Any class implementing this protocol can be used as a completion provider
    in the GROUNDED infrastructure.

    Example:
        class MyCompletionProvider:
            @property
            def name(self) -> str:
                return "my_provider"

            def complete(
                self,
                prompt: str,
                max_tokens: int = 100,
                **kwargs
            ) -> str:
                # Your completion logic here
                return "Generated text..."
    """

    @property
    def name(self) -> str:
        """Provider name identifier."""
        ...

    def complete(
        self,
        prompt: str,
        max_tokens: int = 100,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """
        Generate a completion for the given prompt.

        Args:
            prompt: The prompt to complete
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-2)
            **kwargs: Additional provider-specific parameters

        Returns:
            Generated text completion
        """
        ...

    async def complete_async(
        self,
        prompt: str,
        max_tokens: int = 100,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """
        Async version of complete.

        Args:
            prompt: The prompt to complete
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-2)
            **kwargs: Additional provider-specific parameters

        Returns:
            Generated text completion
        """
        ...


class BaseAIProvider(GroundedComponent):
    """
    Base class for AI providers with common functionality.

    Extends GroundedComponent to add AI-specific utilities and
    lifecycle management. Concrete providers should inherit from
    this class.

    Example:
        class MyProvider(BaseAIProvider):
            @property
            def name(self) -> str:
                return "my_provider"

            @property
            def model_name(self) -> str:
                return "my-model-v1"
    """

    def __init__(
        self,
        model: Optional[str] = None,
        **kwargs: Any,
    ):
        """
        Initialize the AI provider.

        Args:
            model: The model identifier to use
            **kwargs: Additional provider-specific configuration
        """
        self._model = model
        self._config = kwargs

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name identifier."""
        ...

    @property
    def model_name(self) -> Optional[str]:
        """Model being used by this provider."""
        return self._model

    @property
    def config(self) -> Dict[str, Any]:
        """Provider configuration."""
        return self._config.copy()

    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics for this provider.

        Override to provide actual usage tracking.

        Returns:
            Dictionary of usage statistics
        """
        return {
            "provider": self.name,
            "model": self.model_name,
            "calls": 0,
            "tokens": 0,
        }
