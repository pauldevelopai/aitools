"""
GROUNDED Integration Partner Base - Partner integration framework.

Defines the interfaces and base classes for partner integrations,
enabling extensible partnerships with the GROUNDED infrastructure.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from grounded.core.base import ComponentStatus, GroundedComponent, HealthCheckResult, Registry
from grounded.core.config import get_settings


class PartnerCapability(Enum):
    """Capabilities that partners can provide."""

    DATA_SOURCE = "data_source"
    AI_PROVIDER = "ai_provider"
    STORAGE = "storage"
    ANALYTICS = "analytics"
    AUTHENTICATION = "authentication"
    WEBHOOK = "webhook"
    CUSTOM = "custom"


class PartnerStatus(Enum):
    """Status of a partner integration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"
    ERROR = "error"


@dataclass
class PartnerInfo:
    """Information about a partner integration."""

    partner_id: str
    name: str
    description: str = ""
    capabilities: List[PartnerCapability] = field(default_factory=list)
    status: PartnerStatus = PartnerStatus.PENDING
    contact_email: str = ""
    api_version: str = "1.0"
    metadata: Dict[str, Any] = field(default_factory=dict)
    registered_at: datetime = field(default_factory=datetime.utcnow)
    last_active: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "partner_id": self.partner_id,
            "name": self.name,
            "description": self.description,
            "capabilities": [c.value for c in self.capabilities],
            "status": self.status.value,
            "contact_email": self.contact_email,
            "api_version": self.api_version,
            "metadata": self.metadata,
            "registered_at": self.registered_at.isoformat(),
            "last_active": self.last_active.isoformat() if self.last_active else None,
        }


@runtime_checkable
class PartnerIntegrationProtocol(Protocol):
    """
    Protocol for partner integrations.

    Any class implementing this protocol can be registered as a partner
    in the GROUNDED infrastructure.
    """

    @property
    def info(self) -> PartnerInfo:
        """Get partner information."""
        ...

    async def connect(self) -> bool:
        """
        Establish connection to partner service.

        Returns:
            True if connection successful
        """
        ...

    async def disconnect(self) -> None:
        """Disconnect from partner service."""
        ...

    async def health_check(self) -> HealthCheckResult:
        """Check partner integration health."""
        ...


class BasePartnerIntegration(GroundedComponent, ABC):
    """
    Base class for partner integrations.

    Extends GroundedComponent to add partner-specific utilities.
    Concrete partner integrations should inherit from this class.

    Example:
        class MyPartnerIntegration(BasePartnerIntegration):
            @property
            def name(self) -> str:
                return "my_partner"

            @property
            def info(self) -> PartnerInfo:
                return PartnerInfo(
                    partner_id="my_partner_001",
                    name="My Partner",
                    capabilities=[PartnerCapability.DATA_SOURCE]
                )

            async def connect(self) -> bool:
                # Connection logic
                return True

            async def disconnect(self) -> None:
                # Disconnection logic
                pass
    """

    def __init__(
        self,
        partner_id: str,
        partner_name: str,
        capabilities: Optional[List[PartnerCapability]] = None,
        **kwargs: Any,
    ):
        """
        Initialize the partner integration.

        Args:
            partner_id: Unique identifier for this partner
            partner_name: Human-readable partner name
            capabilities: List of capabilities this partner provides
            **kwargs: Additional configuration
        """
        self._partner_id = partner_id
        self._partner_name = partner_name
        self._capabilities = capabilities or []
        self._config = kwargs
        self._status = PartnerStatus.PENDING
        self._connected = False
        self._last_active: Optional[datetime] = None
        self._settings = get_settings()

    @property
    def name(self) -> str:
        """Component name (same as partner_id)."""
        return self._partner_id

    @property
    def info(self) -> PartnerInfo:
        """Get partner information."""
        return PartnerInfo(
            partner_id=self._partner_id,
            name=self._partner_name,
            capabilities=self._capabilities,
            status=self._status,
            last_active=self._last_active,
        )

    @property
    def status(self) -> PartnerStatus:
        """Get current partner status."""
        return self._status

    @property
    def is_connected(self) -> bool:
        """Check if partner is connected."""
        return self._connected

    async def initialize(self) -> None:
        """Initialize the partner integration."""
        await super().initialize()
        # Optionally auto-connect
        # await self.connect()

    async def shutdown(self) -> None:
        """Shutdown the partner integration."""
        if self._connected:
            await self.disconnect()
        await super().shutdown()

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to partner service.

        Returns:
            True if connection successful
        """
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from partner service."""
        ...

    async def health_check(self) -> HealthCheckResult:
        """Check partner integration health."""
        if not self._connected:
            return HealthCheckResult(
                status=ComponentStatus.UNKNOWN,
                component_name=self.name,
                message="Partner not connected",
            )

        # Subclasses should override for actual health checking
        return HealthCheckResult(
            status=ComponentStatus.HEALTHY,
            component_name=self.name,
            message="Partner connected",
            details={"status": self._status.value},
        )

    def _update_last_active(self) -> None:
        """Update the last active timestamp."""
        self._last_active = datetime.utcnow()

    def _set_status(self, status: PartnerStatus) -> None:
        """Update the partner status."""
        self._status = status


# Global partner registry
partner_registry: Registry[BasePartnerIntegration] = Registry(name="partners")


def register_partner(partner: BasePartnerIntegration) -> None:
    """
    Register a partner integration.

    Args:
        partner: The partner integration to register
    """
    partner_registry.register(partner.name, partner)


def get_partner(partner_id: str) -> Optional[BasePartnerIntegration]:
    """
    Get a partner integration by ID.

    Args:
        partner_id: The partner ID to look up

    Returns:
        The partner integration, or None if not found
    """
    return partner_registry.get(partner_id)


def list_partners() -> List[PartnerInfo]:
    """
    List all registered partners.

    Returns:
        List of PartnerInfo for all registered partners
    """
    return [partner.info for _, partner in partner_registry.items()]
