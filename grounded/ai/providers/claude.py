"""
GROUNDED AI Claude Provider - Anthropic Claude completion implementation.

Provides Claude-based text generation for the GROUNDED infrastructure,
implementing the CompletionProvider protocol.
"""

import logging
from typing import Any, Dict, List, Optional

from grounded.ai.providers.base import BaseAIProvider, CompletionProvider
from grounded.core.base import ComponentStatus, HealthCheckResult
from grounded.core.config import get_settings
from grounded.core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class ClaudeCompletionProvider(BaseAIProvider):
    """
    Anthropic Claude completion provider for production use.

    Uses the Anthropic API to generate text completions via Claude models.
    Supports both sync and async operations, system prompts, multi-turn
    conversations, and tool_use for agentic patterns.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
    ):
        super().__init__(model=model)

        self._api_key = api_key
        if not self._api_key:
            raise ConfigurationError(
                setting="ANTHROPIC_API_KEY",
                reason="Anthropic API key is required for Claude completion provider",
                suggestion="Set ANTHROPIC_API_KEY environment variable or pass api_key parameter",
            )

        self._model = model
        self._client: Optional[Any] = None
        self._async_client: Optional[Any] = None
        self._usage_stats = {"calls": 0, "input_tokens": 0, "output_tokens": 0}

    def _get_client(self) -> Any:
        """Get or create sync Anthropic client (lazy initialization)."""
        if self._client is None:
            try:
                from anthropic import Anthropic
                self._client = Anthropic(api_key=self._api_key)
            except ImportError:
                raise ConfigurationError(
                    setting="anthropic",
                    reason="Anthropic package not installed",
                    suggestion="Install with: pip install anthropic",
                )
        return self._client

    def _get_async_client(self) -> Any:
        """Get or create async Anthropic client (lazy initialization)."""
        if self._async_client is None:
            try:
                from anthropic import AsyncAnthropic
                self._async_client = AsyncAnthropic(api_key=self._api_key)
            except ImportError:
                raise ConfigurationError(
                    setting="anthropic",
                    reason="Anthropic package not installed",
                    suggestion="Install with: pip install anthropic",
                )
        return self._async_client

    def _track_usage(self, response: Any) -> None:
        """Track token usage from a response."""
        if hasattr(response, "usage"):
            self._usage_stats["calls"] += 1
            self._usage_stats["input_tokens"] += getattr(response.usage, "input_tokens", 0)
            self._usage_stats["output_tokens"] += getattr(response.usage, "output_tokens", 0)

    @property
    def name(self) -> str:
        return "claude"

    def complete(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """
        Generate a completion using Claude.

        Args:
            prompt: The user message to respond to
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            **kwargs: Additional parameters:
                - system: System prompt string
                - messages: Full message list (overrides prompt)
                - tools: Tool definitions for tool_use
                - stop_sequences: List of stop sequences

        Returns:
            Generated text completion
        """
        client = self._get_client()

        # Build request parameters
        request_params = {
            "model": self._model,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # System prompt
        if "system" in kwargs:
            request_params["system"] = kwargs["system"]

        # Messages — either full list or single user prompt
        if "messages" in kwargs:
            request_params["messages"] = kwargs["messages"]
        else:
            request_params["messages"] = [{"role": "user", "content": prompt}]

        # Tool definitions for agentic patterns
        if "tools" in kwargs:
            request_params["tools"] = kwargs["tools"]

        # Stop sequences
        if "stop_sequences" in kwargs:
            request_params["stop_sequences"] = kwargs["stop_sequences"]

        response = client.messages.create(**request_params)
        self._track_usage(response)

        # Extract text from response content blocks
        text_parts = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)

        return "\n".join(text_parts)

    async def complete_async(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """
        Async version of complete using Claude.

        Args:
            prompt: The user message to respond to
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            **kwargs: Same as complete()

        Returns:
            Generated text completion
        """
        client = self._get_async_client()

        request_params = {
            "model": self._model,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if "system" in kwargs:
            request_params["system"] = kwargs["system"]

        if "messages" in kwargs:
            request_params["messages"] = kwargs["messages"]
        else:
            request_params["messages"] = [{"role": "user", "content": prompt}]

        if "tools" in kwargs:
            request_params["tools"] = kwargs["tools"]

        if "stop_sequences" in kwargs:
            request_params["stop_sequences"] = kwargs["stop_sequences"]

        response = await client.messages.create(**request_params)
        self._track_usage(response)

        text_parts = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)

        return "\n".join(text_parts)

    def create_message(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Any:
        """
        Create a raw message response (for tool_use agentic patterns).

        Returns the full Anthropic response object, not just text.
        This is needed for the Brain engine to inspect stop_reason,
        tool_use blocks, etc.

        Args:
            messages: Conversation messages
            system: System prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            tools: Tool definitions

        Returns:
            Full Anthropic Message response object
        """
        client = self._get_client()

        request_params = {
            "model": self._model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }

        if system:
            request_params["system"] = system
        if tools:
            request_params["tools"] = tools

        response = client.messages.create(**request_params)
        self._track_usage(response)
        return response

    async def create_message_async(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Any:
        """Async version of create_message."""
        client = self._get_async_client()

        request_params = {
            "model": self._model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }

        if system:
            request_params["system"] = system
        if tools:
            request_params["tools"] = tools

        response = await client.messages.create(**request_params)
        self._track_usage(response)
        return response

    async def health_check(self) -> HealthCheckResult:
        """Check provider health by testing API connectivity."""
        try:
            self.complete("Say 'ok'.", max_tokens=10, temperature=0)
            return HealthCheckResult(
                status=ComponentStatus.HEALTHY,
                component_name=self.name,
                message="Anthropic API connection successful",
                details={"model": self._model},
            )
        except Exception as e:
            return HealthCheckResult(
                status=ComponentStatus.UNHEALTHY,
                component_name=self.name,
                message=f"Anthropic API connection failed: {str(e)}",
                details={"error": str(e)},
            )

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for this provider."""
        return {
            "provider": self.name,
            "model": self._model,
            **self._usage_stats,
        }
