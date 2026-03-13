"""Base tool adapter — defines the interface for tool operation adapters.

Adapters don't execute requests server-side. They define the request shape,
and the browser JavaScript executes the actual HTTP calls to localhost.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ToolAction:
    """A single operation a tool can perform."""
    name: str  # e.g. "generate", "list_models"
    label: str  # e.g. "Generate Text"
    description: str
    parameters: list = field(default_factory=list)  # [{name, type, label, required, options}]
    endpoint: str = ""  # Local API endpoint, e.g. "/api/generate"
    method: str = "POST"


@dataclass
class HealthCheck:
    """Health check configuration for a tool."""
    url: str  # e.g. "http://localhost:11434/api/tags"
    method: str = "GET"
    expected_status: int = 200


@dataclass
class InstallStep:
    """Platform-specific installation instructions."""
    platform: str  # "macos", "linux", "windows", "docker"
    commands: list = field(default_factory=list)
    notes: str = ""


class BaseToolAdapter(ABC):
    """Abstract base for tool operation adapters."""

    @abstractmethod
    def get_slug(self) -> str:
        """Return the tool slug matching the kit or app slug."""

    @abstractmethod
    def get_display_name(self) -> str:
        """Return the display name for the tool."""

    @abstractmethod
    def get_base_url(self) -> str:
        """Return the default base URL for the tool's local API."""

    @abstractmethod
    def get_health_check(self) -> HealthCheck:
        """Return the health check configuration."""

    @abstractmethod
    def get_actions(self) -> list[ToolAction]:
        """Return the list of available tool actions."""

    def get_install_steps(self) -> list[InstallStep]:
        """Return platform-specific installation steps."""
        return []

    def build_request(self, action_name: str, params: dict) -> Optional[dict]:
        """Build a request payload for an action.

        Returns:
            Dict with {url, method, body, headers} or None if action not found.
        """
        for action in self.get_actions():
            if action.name == action_name:
                base = self.get_base_url().rstrip("/")
                return {
                    "url": f"{base}{action.endpoint}",
                    "method": action.method,
                    "body": params,
                    "headers": {"Content-Type": "application/json"},
                }
        return None
