"""
Completion service - provides access to the registered Claude completion provider.

All services should import from here instead of using OpenAI directly.

Usage:
    from app.services.completion import get_completion_client

    client = get_completion_client()
    response = client.create_message(
        messages=[{"role": "user", "content": "Hello"}],
        system="You are a helpful assistant.",
    )
    text = response.content[0].text
"""

import logging
from typing import Any

from grounded.ai import get_completion_provider
from grounded.ai.providers.claude import ClaudeCompletionProvider

logger = logging.getLogger(__name__)


def get_completion_client() -> ClaudeCompletionProvider:
    """
    Get the registered Claude completion provider.

    Returns:
        ClaudeCompletionProvider instance

    Raises:
        ProviderNotFoundError: If no completion provider is registered
    """
    provider = get_completion_provider()
    if not isinstance(provider, ClaudeCompletionProvider):
        raise TypeError(
            f"Expected ClaudeCompletionProvider but got {type(provider).__name__}. "
            "Ensure ANTHROPIC_API_KEY is set and Claude is registered as the default provider."
        )
    return provider
