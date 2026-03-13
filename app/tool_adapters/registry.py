"""Tool adapter registry — lookup adapters by tool slug."""
from typing import Optional
from app.tool_adapters.base import BaseToolAdapter
from app.tool_adapters.ollama_adapter import OllamaAdapter
from app.tool_adapters.whisper_adapter import WhisperAdapter

# Built-in adapters keyed by slug
_ADAPTERS: dict[str, BaseToolAdapter] = {
    "ollama": OllamaAdapter(),
    "openai-whisper": WhisperAdapter(),
}


def get_adapter(slug: str) -> Optional[BaseToolAdapter]:
    """Get a tool adapter by slug."""
    return _ADAPTERS.get(slug)


def list_adapters() -> list[str]:
    """List all registered adapter slugs."""
    return list(_ADAPTERS.keys())


def register_adapter(adapter: BaseToolAdapter) -> None:
    """Register a custom adapter at runtime."""
    _ADAPTERS[adapter.get_slug()] = adapter
