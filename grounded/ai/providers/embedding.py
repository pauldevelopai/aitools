"""
GROUNDED AI Embedding Providers - Concrete embedding implementations.

Provides production and development embedding provider implementations
for the GROUNDED infrastructure.
"""

import hashlib
import math
from typing import Any, Dict, List, Optional

from grounded.ai.providers.base import BaseAIProvider, EmbeddingProvider
from grounded.core.base import ComponentStatus, HealthCheckResult
from grounded.core.config import get_settings
from grounded.core.exceptions import ConfigurationError


class LocalStubEmbeddingProvider(BaseAIProvider):
    """
    Local stub embedding provider for development and testing.

    Generates deterministic pseudo-embeddings based on text hashing.
    Useful for development, testing, and offline scenarios.

    Note: These embeddings are NOT semantically meaningful and should
    only be used for development/testing purposes.
    """

    def __init__(self, dimensions: int = 1536):
        """
        Initialize the stub provider.

        Args:
            dimensions: Number of dimensions for embeddings (default: 1536)
        """
        super().__init__(model="local-stub-v1")
        self._dimensions = dimensions

    @property
    def name(self) -> str:
        return "local_stub"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def create_embedding(self, text: str) -> List[float]:
        """
        Create a deterministic pseudo-embedding from text.

        Uses SHA-256 hash to generate reproducible values.

        Args:
            text: The text to embed

        Returns:
            List of floats representing a pseudo-embedding
        """
        # Create hash of text
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

        # Generate deterministic values from hash
        embedding = []
        for i in range(self._dimensions):
            # Use different parts of hash and index to generate values
            seed_str = f"{text_hash}{i}"
            seed_hash = hashlib.md5(seed_str.encode()).hexdigest()
            # Convert first 8 hex chars to float between -1 and 1
            value = (int(seed_hash[:8], 16) / (16**8)) * 2 - 1
            embedding.append(value)

        # Normalize to unit length
        magnitude = math.sqrt(sum(v * v for v in embedding))
        if magnitude > 0:
            embedding = [v / magnitude for v in embedding]

        return embedding

    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Create embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of pseudo-embeddings
        """
        return [self.create_embedding(text) for text in texts]

    async def health_check(self) -> HealthCheckResult:
        """Check provider health (always healthy for stub)."""
        return HealthCheckResult(
            status=ComponentStatus.HEALTHY,
            component_name=self.name,
            message="Local stub provider ready",
            details={"dimensions": self._dimensions},
        )


class OpenAIEmbeddingProvider(BaseAIProvider):
    """
    OpenAI embedding provider for production use.

    Uses the OpenAI API to generate semantic embeddings.
    Requires an API key to be configured.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-small",
        dimensions: Optional[int] = None,
    ):
        """
        Initialize the OpenAI provider.

        Args:
            api_key: OpenAI API key (falls back to settings if not provided)
            model: Embedding model to use
            dimensions: Override default dimensions (model-dependent)

        Raises:
            ConfigurationError: If API key is not provided or configured
        """
        super().__init__(model=model)

        # Get API key from parameter or settings
        self._api_key = api_key or get_settings().openai_api_key
        if not self._api_key:
            raise ConfigurationError(
                setting="GROUNDED_OPENAI_API_KEY",
                reason="OpenAI API key is required for OpenAI embedding provider",
                suggestion="Set GROUNDED_OPENAI_API_KEY environment variable or pass api_key parameter",
            )

        # Set dimensions based on model
        self._model = model
        self._dimensions = dimensions or self._get_default_dimensions(model)
        self._client: Optional[Any] = None

    def _get_default_dimensions(self, model: str) -> int:
        """Get default dimensions for a model."""
        model_dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }
        return model_dimensions.get(model, 1536)

    def _get_client(self) -> Any:
        """Get or create OpenAI client (lazy initialization)."""
        if self._client is None:
            try:
                from openai import OpenAI

                self._client = OpenAI(api_key=self._api_key)
            except ImportError:
                raise ConfigurationError(
                    setting="openai",
                    reason="OpenAI package not installed",
                    suggestion="Install with: pip install openai",
                )
        return self._client

    @property
    def name(self) -> str:
        return "openai"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def create_embedding(self, text: str) -> List[float]:
        """
        Create an embedding using OpenAI API.

        Args:
            text: The text to embed

        Returns:
            Embedding vector from OpenAI
        """
        client = self._get_client()
        response = client.embeddings.create(
            model=self._model,
            input=text,
        )
        return response.data[0].embedding

    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Create embeddings for multiple texts in a single API call.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        client = self._get_client()
        response = client.embeddings.create(
            model=self._model,
            input=texts,
        )

        # Sort by index to maintain order
        sorted_data = sorted(response.data, key=lambda x: x.index)
        return [item.embedding for item in sorted_data]

    async def health_check(self) -> HealthCheckResult:
        """Check provider health by testing API connectivity."""
        try:
            # Test with minimal request
            self.create_embedding("health check")
            return HealthCheckResult(
                status=ComponentStatus.HEALTHY,
                component_name=self.name,
                message="OpenAI API connection successful",
                details={
                    "model": self._model,
                    "dimensions": self._dimensions,
                },
            )
        except Exception as e:
            return HealthCheckResult(
                status=ComponentStatus.UNHEALTHY,
                component_name=self.name,
                message=f"OpenAI API connection failed: {str(e)}",
                details={"error": str(e)},
            )

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for this provider."""
        # In production, this would track actual API usage
        return {
            "provider": self.name,
            "model": self._model,
            "dimensions": self._dimensions,
        }
