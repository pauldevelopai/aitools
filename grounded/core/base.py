"""
GROUNDED Core Base - Component base classes and registries.

Provides the foundational patterns for GROUNDED infrastructure:
- GroundedComponent: Base class with lifecycle management
- Registry: Generic registry pattern for component registration
- ComponentStatus: Enum for component health states
- HealthCheckResult: Structured health check responses
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, Optional, Type, TypeVar

T = TypeVar("T")


class ComponentStatus(Enum):
    """Health status of a GROUNDED component."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a component health check."""

    status: ComponentStatus
    component_name: str
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "status": self.status.value,
            "component": self.component_name,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


class GroundedComponent(ABC):
    """
    Base class for all GROUNDED infrastructure components.

    Provides lifecycle management (initialize, shutdown) and health checking
    capabilities. All major GROUNDED components should inherit from this class.

    Example:
        class MyProvider(GroundedComponent):
            @property
            def name(self) -> str:
                return "my_provider"

            async def initialize(self) -> None:
                # Setup resources
                pass

            async def shutdown(self) -> None:
                # Cleanup resources
                pass

            async def health_check(self) -> HealthCheckResult:
                return HealthCheckResult(
                    status=ComponentStatus.HEALTHY,
                    component_name=self.name
                )
    """

    _initialized: bool = False

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name identifier for this component."""
        ...

    async def initialize(self) -> None:
        """
        Initialize the component.

        Called during application startup. Override to set up resources,
        connections, or other initialization logic.
        """
        self._initialized = True

    async def shutdown(self) -> None:
        """
        Shutdown the component gracefully.

        Called during application shutdown. Override to clean up resources,
        close connections, or perform cleanup logic.
        """
        self._initialized = False

    async def health_check(self) -> HealthCheckResult:
        """
        Perform a health check on this component.

        Override to provide custom health checking logic.

        Returns:
            HealthCheckResult with component status
        """
        return HealthCheckResult(
            status=ComponentStatus.HEALTHY if self._initialized else ComponentStatus.UNKNOWN,
            component_name=self.name,
            message="Component initialized" if self._initialized else "Component not initialized",
        )

    @property
    def is_initialized(self) -> bool:
        """Check if component has been initialized."""
        return self._initialized


class Registry(Generic[T]):
    """
    Generic registry for GROUNDED components.

    Provides a thread-safe way to register, retrieve, and manage components
    by name. Supports default component selection.

    Example:
        registry: Registry[EmbeddingProvider] = Registry()
        registry.register("openai", OpenAIProvider())
        registry.set_default("openai")
        provider = registry.get_default()

    Type Parameters:
        T: The type of components stored in this registry
    """

    def __init__(self, name: str = "unnamed"):
        """
        Initialize a new registry.

        Args:
            name: Human-readable name for this registry (for logging/debugging)
        """
        self._name = name
        self._components: Dict[str, T] = {}
        self._default_key: Optional[str] = None

    @property
    def name(self) -> str:
        """Registry name."""
        return self._name

    def register(self, key: str, component: T, set_as_default: bool = False) -> None:
        """
        Register a component with the given key.

        Args:
            key: Unique identifier for the component
            component: The component instance to register
            set_as_default: If True, set this as the default component
        """
        self._components[key] = component
        if set_as_default or self._default_key is None:
            self._default_key = key

    def unregister(self, key: str) -> Optional[T]:
        """
        Remove and return a component from the registry.

        Args:
            key: The component key to remove

        Returns:
            The removed component, or None if not found
        """
        component = self._components.pop(key, None)
        if self._default_key == key:
            # Reset default to first available or None
            self._default_key = next(iter(self._components), None)
        return component

    def get(self, key: str) -> Optional[T]:
        """
        Get a component by key.

        Args:
            key: The component key to look up

        Returns:
            The component instance, or None if not found
        """
        return self._components.get(key)

    def get_or_raise(self, key: str) -> T:
        """
        Get a component by key, raising an error if not found.

        Args:
            key: The component key to look up

        Returns:
            The component instance

        Raises:
            KeyError: If component not found
        """
        if key not in self._components:
            raise KeyError(f"Component '{key}' not found in registry '{self._name}'")
        return self._components[key]

    def get_default(self) -> Optional[T]:
        """
        Get the default component.

        Returns:
            The default component, or None if no default set
        """
        if self._default_key is None:
            return None
        return self._components.get(self._default_key)

    def set_default(self, key: str) -> None:
        """
        Set the default component.

        Args:
            key: The component key to set as default

        Raises:
            KeyError: If component not found
        """
        if key not in self._components:
            raise KeyError(f"Cannot set default: '{key}' not in registry '{self._name}'")
        self._default_key = key

    def list_keys(self) -> list[str]:
        """Get list of all registered component keys."""
        return list(self._components.keys())

    def items(self) -> list[tuple[str, T]]:
        """Get all registered components as (key, component) pairs."""
        return list(self._components.items())

    def __contains__(self, key: str) -> bool:
        """Check if a key is registered."""
        return key in self._components

    def __len__(self) -> int:
        """Get number of registered components."""
        return len(self._components)

    def __iter__(self):
        """Iterate over component keys."""
        return iter(self._components)
