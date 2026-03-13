"""
GROUNDED AI Ollama Provider - Local open-source LLM completion and embedding.

Provides Ollama-based text generation and embeddings for the GROUNDED infrastructure,
implementing the CompletionProvider and EmbeddingProvider protocols.

Ollama runs locally (free, open-source) and supports tool_use via its
OpenAI-compatible chat endpoint. This provider translates between Ollama's
response format and the Anthropic-compatible shape expected by the Brain engine.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from grounded.ai.providers.base import BaseAIProvider, EmbeddingProvider
from grounded.core.base import ComponentStatus, HealthCheckResult

logger = logging.getLogger(__name__)

# Default timeout for Ollama requests (local, so can be generous)
OLLAMA_TIMEOUT = 120.0


# ---------------------------------------------------------------------------
# Response wrapper dataclasses — match Anthropic's response shape so the
# Brain engine (app/brain/engine.py) works without modification.
# ---------------------------------------------------------------------------

@dataclass
class OllamaContentBlock:
    """Mimics Anthropic's ContentBlock (TextBlock or ToolUseBlock)."""
    type: str  # "text" or "tool_use"
    text: str = ""
    id: str = ""
    name: str = ""
    input: dict = field(default_factory=dict)


@dataclass
class OllamaUsage:
    """Mimics Anthropic's Usage object."""
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class OllamaMessageResponse:
    """Mimics Anthropic's Message response object.

    The Brain engine inspects:
      - response.stop_reason == "end_turn"
      - response.content (list of blocks)
      - block.type == "text" / "tool_use"
      - block.id, block.name, block.input (for tool calls)
      - response.usage.input_tokens / output_tokens
    """
    content: list  # list[OllamaContentBlock]
    stop_reason: str  # "end_turn" or "tool_use"
    usage: OllamaUsage = field(default_factory=OllamaUsage)


# ---------------------------------------------------------------------------
# Schema translation helpers
# ---------------------------------------------------------------------------

def _anthropic_tools_to_ollama(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert Anthropic tool schemas to Ollama/OpenAI format.

    Anthropic uses: {"name": ..., "description": ..., "input_schema": {...}}
    Ollama/OpenAI uses: {"type": "function", "function": {"name": ..., "description": ..., "parameters": {...}}}
    """
    ollama_tools = []
    for tool in tools:
        ollama_tools.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema", {}),
            },
        })
    return ollama_tools


def _ollama_response_to_wrapper(data: Dict[str, Any]) -> OllamaMessageResponse:
    """Convert Ollama /api/chat response to Anthropic-compatible wrapper.

    Ollama response shape:
    {
        "message": {
            "role": "assistant",
            "content": "text...",
            "tool_calls": [{"id": "...", "function": {"name": "...", "arguments": {...}}}]
        },
        "done": true,
        "prompt_eval_count": N,
        "eval_count": N,
    }
    """
    message = data.get("message", {})
    content_blocks = []

    # Extract text content
    text = message.get("content", "")
    if text:
        content_blocks.append(OllamaContentBlock(type="text", text=text))

    # Extract tool calls
    tool_calls = message.get("tool_calls", [])
    has_tool_use = len(tool_calls) > 0

    for tc in tool_calls:
        func = tc.get("function", {})
        # Ollama sometimes returns arguments as a string, sometimes as dict
        arguments = func.get("arguments", {})
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except (json.JSONDecodeError, TypeError):
                arguments = {}

        content_blocks.append(OllamaContentBlock(
            type="tool_use",
            id=tc.get("id", f"toolu_{uuid.uuid4().hex[:24]}"),
            name=func.get("name", ""),
            input=arguments,
        ))

    # Determine stop reason
    stop_reason = "tool_use" if has_tool_use else "end_turn"

    # Token usage
    usage = OllamaUsage(
        input_tokens=data.get("prompt_eval_count", 0),
        output_tokens=data.get("eval_count", 0),
    )

    return OllamaMessageResponse(
        content=content_blocks,
        stop_reason=stop_reason,
        usage=usage,
    )


def _build_ollama_messages(
    messages: List[Dict[str, Any]],
    system: Optional[str] = None,
) -> tuple[List[Dict[str, Any]], Optional[str]]:
    """Convert Anthropic-style messages to Ollama/OpenAI chat format.

    Handles:
    - System prompt as separate parameter or first message
    - Tool results: Anthropic sends as user messages with tool_result content blocks
    - Assistant messages with content blocks (text + tool_use mixed)
    """
    ollama_messages = []

    for msg in messages:
        role = msg["role"]
        content = msg["content"]

        if role == "assistant":
            # Content may be a list of Anthropic-style content blocks or wrappers
            if isinstance(content, list):
                # Extract text from blocks
                text_parts = []
                tool_calls = []
                for block in content:
                    if isinstance(block, OllamaContentBlock):
                        if block.type == "text" and block.text:
                            text_parts.append(block.text)
                        elif block.type == "tool_use":
                            tool_calls.append({
                                "id": block.id,
                                "type": "function",
                                "function": {
                                    "name": block.name,
                                    "arguments": json.dumps(block.input),
                                },
                            })
                    elif isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif block.get("type") == "tool_use":
                            tool_calls.append({
                                "id": block.get("id", ""),
                                "type": "function",
                                "function": {
                                    "name": block.get("name", ""),
                                    "arguments": json.dumps(block.get("input", {})),
                                },
                            })

                assistant_msg = {"role": "assistant", "content": "\n".join(text_parts) or ""}
                if tool_calls:
                    assistant_msg["tool_calls"] = tool_calls
                ollama_messages.append(assistant_msg)

            elif isinstance(content, str):
                ollama_messages.append({"role": "assistant", "content": content})

        elif role == "user":
            if isinstance(content, list):
                # May be tool_result blocks from Brain engine
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "tool_result":
                        ollama_messages.append({
                            "role": "tool",
                            "content": str(item.get("content", "")),
                            "tool_call_id": item.get("tool_use_id", ""),
                        })
                    elif isinstance(item, dict) and item.get("type") == "text":
                        ollama_messages.append({"role": "user", "content": item.get("text", "")})
                    else:
                        # Fallback: serialize as text
                        ollama_messages.append({"role": "user", "content": str(item)})
            elif isinstance(content, str):
                ollama_messages.append({"role": "user", "content": content})

        elif role == "system":
            # Prepend as system if not already handled
            system = content if isinstance(content, str) else str(content)

    return ollama_messages, system


# ---------------------------------------------------------------------------
# Ollama Completion Provider
# ---------------------------------------------------------------------------

class OllamaCompletionProvider(BaseAIProvider):
    """
    Ollama local LLM completion provider.

    Uses Ollama's /api/chat endpoint for chat completions with tool support.
    Translates responses to match Anthropic's response shape so the Brain
    engine and other services work without modification.

    Requires Ollama to be running (default: http://localhost:11434).
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.1",
    ):
        super().__init__(model=model)
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._usage_stats = {"calls": 0, "input_tokens": 0, "output_tokens": 0}

    def _track_usage(self, response: OllamaMessageResponse) -> None:
        """Track token usage from a response."""
        self._usage_stats["calls"] += 1
        self._usage_stats["input_tokens"] += response.usage.input_tokens
        self._usage_stats["output_tokens"] += response.usage.output_tokens

    @property
    def name(self) -> str:
        return "ollama"

    def complete(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """Generate a completion using Ollama."""
        # Build messages
        messages = kwargs.get("messages", [{"role": "user", "content": prompt}])
        system = kwargs.get("system")

        ollama_messages, system_prompt = _build_ollama_messages(messages, system)

        payload: Dict[str, Any] = {
            "model": self._model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }

        if system_prompt:
            # Prepend system message
            payload["messages"] = [{"role": "system", "content": system_prompt}] + payload["messages"]

        # Add tools if provided
        tools = kwargs.get("tools")
        if tools:
            payload["tools"] = _anthropic_tools_to_ollama(tools)

        with httpx.Client(timeout=OLLAMA_TIMEOUT) as client:
            resp = client.post(f"{self._base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()

        wrapper = _ollama_response_to_wrapper(data)
        self._track_usage(wrapper)

        # Return text only
        text_parts = [b.text for b in wrapper.content if b.type == "text" and b.text]
        return "\n".join(text_parts)

    async def complete_async(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """Async version of complete using Ollama."""
        messages = kwargs.get("messages", [{"role": "user", "content": prompt}])
        system = kwargs.get("system")

        ollama_messages, system_prompt = _build_ollama_messages(messages, system)

        payload: Dict[str, Any] = {
            "model": self._model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }

        if system_prompt:
            payload["messages"] = [{"role": "system", "content": system_prompt}] + payload["messages"]

        tools = kwargs.get("tools")
        if tools:
            payload["tools"] = _anthropic_tools_to_ollama(tools)

        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            resp = await client.post(f"{self._base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()

        wrapper = _ollama_response_to_wrapper(data)
        self._track_usage(wrapper)

        text_parts = [b.text for b in wrapper.content if b.type == "text" and b.text]
        return "\n".join(text_parts)

    def create_message(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> OllamaMessageResponse:
        """Create a raw message response (for tool_use agentic patterns).

        Returns an OllamaMessageResponse that matches Anthropic's response shape:
        - response.content (list of OllamaContentBlock)
        - response.stop_reason ("end_turn" or "tool_use")
        - response.usage.input_tokens / output_tokens
        """
        ollama_messages, system_prompt = _build_ollama_messages(messages, system)

        payload: Dict[str, Any] = {
            "model": self._model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }

        if system_prompt:
            payload["messages"] = [{"role": "system", "content": system_prompt}] + payload["messages"]

        if tools:
            payload["tools"] = _anthropic_tools_to_ollama(tools)

        with httpx.Client(timeout=OLLAMA_TIMEOUT) as client:
            resp = client.post(f"{self._base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()

        wrapper = _ollama_response_to_wrapper(data)
        self._track_usage(wrapper)
        return wrapper

    async def create_message_async(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> OllamaMessageResponse:
        """Async version of create_message."""
        ollama_messages, system_prompt = _build_ollama_messages(messages, system)

        payload: Dict[str, Any] = {
            "model": self._model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }

        if system_prompt:
            payload["messages"] = [{"role": "system", "content": system_prompt}] + payload["messages"]

        if tools:
            payload["tools"] = _anthropic_tools_to_ollama(tools)

        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            resp = await client.post(f"{self._base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()

        wrapper = _ollama_response_to_wrapper(data)
        self._track_usage(wrapper)
        return wrapper

    async def health_check(self) -> HealthCheckResult:
        """Check Ollama connectivity and model availability."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self._base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()

            models = [m["name"] for m in data.get("models", [])]
            model_available = any(self._model in m for m in models)

            if model_available:
                return HealthCheckResult(
                    status=ComponentStatus.HEALTHY,
                    component_name=self.name,
                    message=f"Ollama running with {self._model}",
                    details={"model": self._model, "available_models": models},
                )
            else:
                return HealthCheckResult(
                    status=ComponentStatus.DEGRADED,
                    component_name=self.name,
                    message=f"Ollama running but {self._model} not pulled. Run: ollama pull {self._model}",
                    details={"model": self._model, "available_models": models},
                )

        except Exception as e:
            return HealthCheckResult(
                status=ComponentStatus.UNHEALTHY,
                component_name=self.name,
                message=f"Ollama not reachable at {self._base_url}: {e}",
                details={"error": str(e), "base_url": self._base_url},
            )

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for this provider."""
        return {
            "provider": self.name,
            "model": self._model,
            "base_url": self._base_url,
            **self._usage_stats,
        }


# ---------------------------------------------------------------------------
# Ollama Embedding Provider
# ---------------------------------------------------------------------------

class OllamaEmbeddingProvider(BaseAIProvider):
    """
    Ollama local embedding provider.

    Uses Ollama's /api/embed endpoint with models like nomic-embed-text
    or mxbai-embed-large. Runs locally — free, no API keys needed.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
        dimensions: int = 768,
    ):
        super().__init__(model=model)
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._dimensions = dimensions

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def create_embedding(self, text: str) -> List[float]:
        """Create an embedding using Ollama."""
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{self._base_url}/api/embed",
                json={"model": self._model, "input": text},
            )
            resp.raise_for_status()
            data = resp.json()

        # Ollama /api/embed returns {"embeddings": [[float, ...]]}
        embeddings = data.get("embeddings", [])
        if embeddings:
            return embeddings[0]

        # Fallback: older Ollama versions use /api/embeddings
        logger.warning("Ollama /api/embed returned empty, trying /api/embeddings")
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{self._base_url}/api/embeddings",
                json={"model": self._model, "prompt": text},
            )
            resp.raise_for_status()
            data = resp.json()

        return data.get("embedding", [0.0] * self._dimensions)

    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for multiple texts."""
        # Ollama /api/embed supports batch via "input" as list
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                f"{self._base_url}/api/embed",
                json={"model": self._model, "input": texts},
            )
            resp.raise_for_status()
            data = resp.json()

        embeddings = data.get("embeddings", [])
        if len(embeddings) == len(texts):
            return embeddings

        # Fallback: one at a time
        return [self.create_embedding(t) for t in texts]

    async def health_check(self) -> HealthCheckResult:
        """Check Ollama embedding model availability."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self._base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()

            models = [m["name"] for m in data.get("models", [])]
            model_available = any(self._model in m for m in models)

            if model_available:
                return HealthCheckResult(
                    status=ComponentStatus.HEALTHY,
                    component_name=f"{self.name}_embedding",
                    message=f"Ollama embedding model {self._model} available",
                    details={"model": self._model, "dimensions": self._dimensions},
                )
            else:
                return HealthCheckResult(
                    status=ComponentStatus.DEGRADED,
                    component_name=f"{self.name}_embedding",
                    message=f"Model {self._model} not pulled. Run: ollama pull {self._model}",
                    details={"model": self._model, "available_models": models},
                )

        except Exception as e:
            return HealthCheckResult(
                status=ComponentStatus.UNHEALTHY,
                component_name=f"{self.name}_embedding",
                message=f"Ollama not reachable: {e}",
                details={"error": str(e)},
            )

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for this provider."""
        return {
            "provider": self.name,
            "model": self._model,
            "dimensions": self._dimensions,
            "base_url": self._base_url,
        }
