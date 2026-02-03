"""
GROUNDED AI Governed Providers - Provider wrappers with automatic tracking.

Provides wrapper classes that automatically track all AI provider operations
in the governance audit trail. These wrappers can be used as drop-in
replacements for standard providers.

Usage:
    from grounded.governance.ai import GovernedEmbeddingProvider

    # Wrap an existing provider
    base_provider = OpenAIEmbeddingProvider(api_key="...")
    governed = GovernedEmbeddingProvider(base_provider)

    # All operations are now automatically tracked
    embedding = governed.create_embedding("Hello, world!")
"""

import logging
from typing import Any, Dict, List, Optional

from grounded.ai.providers.base import EmbeddingProvider, CompletionProvider
from grounded.governance.ai.models import AIDataType, AIOperationType
from grounded.governance.ai.tracker import get_governance_tracker

logger = logging.getLogger(__name__)


class GovernedEmbeddingProvider:
    """
    Wrapper for EmbeddingProvider that automatically tracks all operations.

    This wrapper implements the EmbeddingProvider protocol and delegates
    all operations to an underlying provider while recording them in
    the AI governance audit trail.

    Example:
        base = OpenAIEmbeddingProvider(api_key="...")
        governed = GovernedEmbeddingProvider(base, source_component="DocumentProcessor")

        # All calls are now tracked
        embedding = governed.create_embedding("text")

        # Check audit trail
        records = tracker.get_records(operation_type=AIOperationType.EMBEDDING)
    """

    def __init__(
        self,
        provider: EmbeddingProvider,
        source_component: str = "",
        actor_type: str = "system",
        actor_id: Optional[str] = None,
    ):
        """
        Initialize the governed provider.

        Args:
            provider: The underlying embedding provider
            source_component: Component name for audit records
            actor_type: Actor type for audit records
            actor_id: Actor ID for audit records
        """
        self._provider = provider
        self._source_component = source_component or provider.name
        self._actor_type = actor_type
        self._actor_id = actor_id

    @property
    def name(self) -> str:
        """Provider name (from underlying provider)."""
        return self._provider.name

    @property
    def dimensions(self) -> int:
        """Embedding dimensions (from underlying provider)."""
        return self._provider.dimensions

    @property
    def base_provider(self) -> EmbeddingProvider:
        """Access to the underlying provider."""
        return self._provider

    def create_embedding(self, text: str) -> List[float]:
        """
        Create an embedding for a single text (tracked).

        Args:
            text: The text to embed

        Returns:
            Embedding vector
        """
        tracker = get_governance_tracker()

        # Start tracking
        record = tracker.start_operation(
            operation_type=AIOperationType.EMBEDDING,
            source_component=self._source_component,
            source_module="grounded.governance.ai.providers",
            source_function="create_embedding",
            provider_name=self._provider.name,
            model_name=getattr(self._provider, "model_name", "") or "",
            input_data_type=AIDataType.TEXT,
            input_size=len(text),
            input_count=1,
            actor_type=self._actor_type,
            actor_id=self._actor_id,
        )

        try:
            # Execute the actual operation
            result = self._provider.create_embedding(text)

            # Complete tracking
            tracker.complete_operation(
                record.record_id,
                output_size=len(result),
                output_count=1,
                output_data_type=AIDataType.EMBEDDING_VECTOR,
            )

            return result

        except Exception as e:
            tracker.fail_operation(
                record.record_id,
                error_message=str(e),
                error_type=type(e).__name__,
            )
            raise

    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Create embeddings for multiple texts (tracked as batch).

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        tracker = get_governance_tracker()

        # Calculate total input size
        total_size = sum(len(t) for t in texts)

        # Start tracking
        record = tracker.start_operation(
            operation_type=AIOperationType.EMBEDDING_BATCH,
            source_component=self._source_component,
            source_module="grounded.governance.ai.providers",
            source_function="create_embeddings",
            provider_name=self._provider.name,
            model_name=getattr(self._provider, "model_name", "") or "",
            input_data_type=AIDataType.TEXT,
            input_size=total_size,
            input_count=len(texts),
            actor_type=self._actor_type,
            actor_id=self._actor_id,
            batch_size=len(texts),
        )

        try:
            # Execute the actual operation
            results = self._provider.create_embeddings(texts)

            # Complete tracking
            total_output = sum(len(r) for r in results)
            tracker.complete_operation(
                record.record_id,
                output_size=total_output,
                output_count=len(results),
                output_data_type=AIDataType.EMBEDDING_VECTOR,
            )

            return results

        except Exception as e:
            tracker.fail_operation(
                record.record_id,
                error_message=str(e),
                error_type=type(e).__name__,
            )
            raise


class GovernedCompletionProvider:
    """
    Wrapper for CompletionProvider that automatically tracks all operations.

    Similar to GovernedEmbeddingProvider but for completion/generation operations.
    """

    def __init__(
        self,
        provider: CompletionProvider,
        source_component: str = "",
        actor_type: str = "system",
        actor_id: Optional[str] = None,
    ):
        """
        Initialize the governed provider.

        Args:
            provider: The underlying completion provider
            source_component: Component name for audit records
            actor_type: Actor type for audit records
            actor_id: Actor ID for audit records
        """
        self._provider = provider
        self._source_component = source_component or provider.name
        self._actor_type = actor_type
        self._actor_id = actor_id

    @property
    def name(self) -> str:
        """Provider name (from underlying provider)."""
        return self._provider.name

    @property
    def base_provider(self) -> CompletionProvider:
        """Access to the underlying provider."""
        return self._provider

    def complete(
        self,
        prompt: str,
        max_tokens: int = 100,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """
        Generate a completion (tracked).

        Args:
            prompt: The prompt to complete
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional provider-specific parameters

        Returns:
            Generated text
        """
        tracker = get_governance_tracker()

        # Estimate input tokens (rough approximation)
        estimated_input_tokens = len(prompt.split()) * 1.3

        record = tracker.start_operation(
            operation_type=AIOperationType.COMPLETION,
            source_component=self._source_component,
            source_module="grounded.governance.ai.providers",
            source_function="complete",
            provider_name=self._provider.name,
            model_name=getattr(self._provider, "model_name", "") or "",
            input_data_type=AIDataType.TEXT,
            input_size=len(prompt),
            input_count=1,
            tokens_input=int(estimated_input_tokens),
            actor_type=self._actor_type,
            actor_id=self._actor_id,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        try:
            result = self._provider.complete(
                prompt, max_tokens=max_tokens, temperature=temperature, **kwargs
            )

            # Estimate output tokens
            estimated_output_tokens = len(result.split()) * 1.3

            tracker.complete_operation(
                record.record_id,
                output_size=len(result),
                output_count=1,
                output_data_type=AIDataType.TEXT,
                tokens_output=int(estimated_output_tokens),
            )

            return result

        except Exception as e:
            tracker.fail_operation(
                record.record_id,
                error_message=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def complete_async(
        self,
        prompt: str,
        max_tokens: int = 100,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """
        Async version of complete (tracked).

        Args:
            prompt: The prompt to complete
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional provider-specific parameters

        Returns:
            Generated text
        """
        tracker = get_governance_tracker()

        estimated_input_tokens = len(prompt.split()) * 1.3

        record = tracker.start_operation(
            operation_type=AIOperationType.COMPLETION,
            source_component=self._source_component,
            source_module="grounded.governance.ai.providers",
            source_function="complete_async",
            provider_name=self._provider.name,
            model_name=getattr(self._provider, "model_name", "") or "",
            input_data_type=AIDataType.TEXT,
            input_size=len(prompt),
            input_count=1,
            tokens_input=int(estimated_input_tokens),
            actor_type=self._actor_type,
            actor_id=self._actor_id,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        try:
            result = await self._provider.complete_async(
                prompt, max_tokens=max_tokens, temperature=temperature, **kwargs
            )

            estimated_output_tokens = len(result.split()) * 1.3

            tracker.complete_operation(
                record.record_id,
                output_size=len(result),
                output_count=1,
                output_data_type=AIDataType.TEXT,
                tokens_output=int(estimated_output_tokens),
            )

            return result

        except Exception as e:
            tracker.fail_operation(
                record.record_id,
                error_message=str(e),
                error_type=type(e).__name__,
            )
            raise


def wrap_embedding_provider(
    provider: EmbeddingProvider,
    source_component: str = "",
    actor_type: str = "system",
    actor_id: Optional[str] = None,
) -> GovernedEmbeddingProvider:
    """
    Convenience function to wrap an embedding provider with governance tracking.

    Args:
        provider: The provider to wrap
        source_component: Component name for audit records
        actor_type: Actor type for audit records
        actor_id: Actor ID for audit records

    Returns:
        GovernedEmbeddingProvider wrapping the original provider
    """
    return GovernedEmbeddingProvider(
        provider=provider,
        source_component=source_component,
        actor_type=actor_type,
        actor_id=actor_id,
    )


def wrap_completion_provider(
    provider: CompletionProvider,
    source_component: str = "",
    actor_type: str = "system",
    actor_id: Optional[str] = None,
) -> GovernedCompletionProvider:
    """
    Convenience function to wrap a completion provider with governance tracking.

    Args:
        provider: The provider to wrap
        source_component: Component name for audit records
        actor_type: Actor type for audit records
        actor_id: Actor ID for audit records

    Returns:
        GovernedCompletionProvider wrapping the original provider
    """
    return GovernedCompletionProvider(
        provider=provider,
        source_component=source_component,
        actor_type=actor_type,
        actor_id=actor_id,
    )
