"""
GROUNDED Interface Capabilities - Registry of available capabilities.

Defines what capabilities are exposed by GROUNDED, their access controls,
rate limits, and configuration for civic tool integration.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict
import threading

from grounded.interface.models import CapabilityType, CapabilityInfo


class AccessLevel(Enum):
    """Access levels for capabilities."""

    PUBLIC = "public"          # No authentication required
    AUTHENTICATED = "authenticated"  # Requires valid client ID
    PARTNER = "partner"        # Requires partner agreement
    ADMIN = "admin"            # Requires admin access


@dataclass
class CapabilityDefinition:
    """
    Definition of a capability including access control and limits.

    Defines the full specification of a capability that GROUNDED exposes
    to external civic tools.
    """

    capability_type: CapabilityType
    name: str
    description: str
    access_level: AccessLevel = AccessLevel.AUTHENTICATED
    enabled: bool = True
    rate_limit_per_minute: Optional[int] = None
    rate_limit_per_hour: Optional[int] = None
    rate_limit_per_day: Optional[int] = None
    requires_knowledge_base: bool = False
    max_input_size: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_capability_info(self) -> CapabilityInfo:
        """Convert to CapabilityInfo for API responses."""
        return CapabilityInfo(
            capability=self.capability_type,
            name=self.name,
            description=self.description,
            enabled=self.enabled,
            requires_auth=self.access_level != AccessLevel.PUBLIC,
            rate_limit=self.rate_limit_per_minute,
        )


# Default capability definitions
DEFAULT_CAPABILITIES: Dict[CapabilityType, CapabilityDefinition] = {
    # AI Processing
    CapabilityType.EMBEDDING: CapabilityDefinition(
        capability_type=CapabilityType.EMBEDDING,
        name="Generate Embedding",
        description="Generate a vector embedding for text using AI models",
        access_level=AccessLevel.AUTHENTICATED,
        rate_limit_per_minute=60,
        rate_limit_per_hour=1000,
        max_input_size=8000,  # characters
    ),
    CapabilityType.EMBEDDING_BATCH: CapabilityDefinition(
        capability_type=CapabilityType.EMBEDDING_BATCH,
        name="Batch Embeddings",
        description="Generate embeddings for multiple texts in a single request",
        access_level=AccessLevel.AUTHENTICATED,
        rate_limit_per_minute=20,
        rate_limit_per_hour=200,
        max_input_size=50000,  # total characters
        metadata={"max_batch_size": 100},
    ),
    CapabilityType.COMPLETION: CapabilityDefinition(
        capability_type=CapabilityType.COMPLETION,
        name="Text Completion",
        description="Generate text completions using AI models (future)",
        access_level=AccessLevel.PARTNER,
        enabled=False,  # Not yet implemented
        rate_limit_per_minute=30,
    ),

    # Knowledge System
    CapabilityType.KNOWLEDGE_BASE_MANAGE: CapabilityDefinition(
        capability_type=CapabilityType.KNOWLEDGE_BASE_MANAGE,
        name="Knowledge Base Management",
        description="Create, update, and manage knowledge bases and their contents",
        access_level=AccessLevel.AUTHENTICATED,
        rate_limit_per_minute=30,
        rate_limit_per_hour=500,
    ),
    CapabilityType.KNOWLEDGE_SEARCH: CapabilityDefinition(
        capability_type=CapabilityType.KNOWLEDGE_SEARCH,
        name="Knowledge Search",
        description="Search knowledge bases using text or semantic queries",
        access_level=AccessLevel.AUTHENTICATED,
        rate_limit_per_minute=100,
        rate_limit_per_hour=2000,
        requires_knowledge_base=True,
    ),
    CapabilityType.KNOWLEDGE_ANSWER: CapabilityDefinition(
        capability_type=CapabilityType.KNOWLEDGE_ANSWER,
        name="Grounded Answers",
        description="Get answers grounded in knowledge sources with citations",
        access_level=AccessLevel.AUTHENTICATED,
        rate_limit_per_minute=30,
        rate_limit_per_hour=500,
        requires_knowledge_base=True,
    ),

    # Document Processing
    CapabilityType.DOCUMENT_PROCESS: CapabilityDefinition(
        capability_type=CapabilityType.DOCUMENT_PROCESS,
        name="Document Processing",
        description="Process documents with extraction, chunking, and embedding",
        access_level=AccessLevel.AUTHENTICATED,
        rate_limit_per_minute=20,
        rate_limit_per_hour=200,
        max_input_size=100000,  # characters
    ),
    CapabilityType.DOCUMENT_CHUNK: CapabilityDefinition(
        capability_type=CapabilityType.DOCUMENT_CHUNK,
        name="Document Chunking",
        description="Split documents into semantic chunks",
        access_level=AccessLevel.AUTHENTICATED,
        rate_limit_per_minute=30,
        rate_limit_per_hour=500,
        max_input_size=100000,
    ),

    # Governance
    CapabilityType.GOVERNANCE_STATS: CapabilityDefinition(
        capability_type=CapabilityType.GOVERNANCE_STATS,
        name="Governance Statistics",
        description="View AI operation statistics and usage metrics",
        access_level=AccessLevel.AUTHENTICATED,
        rate_limit_per_minute=30,
    ),
    CapabilityType.GOVERNANCE_AUDIT: CapabilityDefinition(
        capability_type=CapabilityType.GOVERNANCE_AUDIT,
        name="Audit Trail",
        description="Access detailed audit trail of AI operations",
        access_level=AccessLevel.PARTNER,
        rate_limit_per_minute=10,
    ),

    # System
    CapabilityType.HEALTH_CHECK: CapabilityDefinition(
        capability_type=CapabilityType.HEALTH_CHECK,
        name="Health Check",
        description="Check system health and component status",
        access_level=AccessLevel.PUBLIC,
        rate_limit_per_minute=60,
    ),
    CapabilityType.CAPABILITY_LIST: CapabilityDefinition(
        capability_type=CapabilityType.CAPABILITY_LIST,
        name="List Capabilities",
        description="List available capabilities and their status",
        access_level=AccessLevel.PUBLIC,
        rate_limit_per_minute=60,
    ),
}


@dataclass
class RateLimitStatus:
    """Current rate limit status for a client."""

    requests_this_minute: int = 0
    requests_this_hour: int = 0
    requests_this_day: int = 0
    minute_window_start: datetime = field(default_factory=datetime.utcnow)
    hour_window_start: datetime = field(default_factory=datetime.utcnow)
    day_window_start: datetime = field(default_factory=datetime.utcnow)


class CapabilityRegistry:
    """
    Registry of available capabilities with access control and rate limiting.

    Manages capability definitions, client permissions, and enforces
    rate limits for the GROUNDED interface.

    Example:
        registry = CapabilityRegistry()

        # Check if client can use a capability
        if registry.can_use_capability("client-123", CapabilityType.EMBEDDING):
            # Record usage
            registry.record_usage("client-123", CapabilityType.EMBEDDING)
    """

    def __init__(self):
        """Initialize the capability registry with default capabilities."""
        self._capabilities: Dict[CapabilityType, CapabilityDefinition] = dict(DEFAULT_CAPABILITIES)
        self._client_permissions: Dict[str, Set[CapabilityType]] = defaultdict(set)
        self._client_access_levels: Dict[str, AccessLevel] = {}
        self._rate_limits: Dict[str, Dict[CapabilityType, RateLimitStatus]] = defaultdict(
            lambda: defaultdict(RateLimitStatus)
        )
        self._lock = threading.Lock()

    def get_capability(self, capability_type: CapabilityType) -> Optional[CapabilityDefinition]:
        """Get a capability definition."""
        return self._capabilities.get(capability_type)

    def list_capabilities(
        self,
        enabled_only: bool = True,
        access_level: Optional[AccessLevel] = None,
    ) -> List[CapabilityDefinition]:
        """
        List available capabilities.

        Args:
            enabled_only: Only return enabled capabilities
            access_level: Filter by maximum access level

        Returns:
            List of capability definitions
        """
        result = []
        for cap in self._capabilities.values():
            if enabled_only and not cap.enabled:
                continue
            if access_level and cap.access_level.value > access_level.value:
                continue
            result.append(cap)
        return result

    def register_client(
        self,
        client_id: str,
        access_level: AccessLevel = AccessLevel.AUTHENTICATED,
        allowed_capabilities: Optional[Set[CapabilityType]] = None,
    ) -> None:
        """
        Register a client with specific access level and permissions.

        Args:
            client_id: Unique client identifier
            access_level: Access level for the client
            allowed_capabilities: Specific capabilities to allow (None = all for level)
        """
        with self._lock:
            self._client_access_levels[client_id] = access_level

            if allowed_capabilities:
                self._client_permissions[client_id] = allowed_capabilities
            else:
                # Grant all capabilities at or below the client's access level
                self._client_permissions[client_id] = {
                    cap.capability_type
                    for cap in self._capabilities.values()
                    if cap.enabled and self._access_level_value(cap.access_level) <= self._access_level_value(access_level)
                }

    def _access_level_value(self, level: AccessLevel) -> int:
        """Get numeric value for access level comparison."""
        values = {
            AccessLevel.PUBLIC: 0,
            AccessLevel.AUTHENTICATED: 1,
            AccessLevel.PARTNER: 2,
            AccessLevel.ADMIN: 3,
        }
        return values.get(level, 0)

    def get_client_access_level(self, client_id: str) -> AccessLevel:
        """Get the access level for a client."""
        return self._client_access_levels.get(client_id, AccessLevel.AUTHENTICATED)

    def can_use_capability(
        self,
        client_id: str,
        capability_type: CapabilityType,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a client can use a capability.

        Returns:
            Tuple of (allowed, reason if not allowed)
        """
        capability = self._capabilities.get(capability_type)
        if not capability:
            return False, "Capability not found"

        if not capability.enabled:
            return False, "Capability is disabled"

        # Check access level
        client_level = self.get_client_access_level(client_id)
        if self._access_level_value(capability.access_level) > self._access_level_value(client_level):
            return False, f"Insufficient access level (requires {capability.access_level.value})"

        # Check specific permissions if set
        if client_id in self._client_permissions:
            if capability_type not in self._client_permissions[client_id]:
                return False, "Capability not in allowed list"

        # Check rate limits
        rate_limited, reason = self._check_rate_limit(client_id, capability_type)
        if rate_limited:
            return False, reason

        return True, None

    def _check_rate_limit(
        self,
        client_id: str,
        capability_type: CapabilityType,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if client has exceeded rate limits.

        Returns:
            Tuple of (is_rate_limited, reason)
        """
        capability = self._capabilities.get(capability_type)
        if not capability:
            return False, None

        with self._lock:
            status = self._rate_limits[client_id][capability_type]
            now = datetime.utcnow()

            # Reset windows if expired
            if now - status.minute_window_start > timedelta(minutes=1):
                status.requests_this_minute = 0
                status.minute_window_start = now

            if now - status.hour_window_start > timedelta(hours=1):
                status.requests_this_hour = 0
                status.hour_window_start = now

            if now - status.day_window_start > timedelta(days=1):
                status.requests_this_day = 0
                status.day_window_start = now

            # Check limits
            if capability.rate_limit_per_minute and status.requests_this_minute >= capability.rate_limit_per_minute:
                return True, f"Rate limit exceeded ({capability.rate_limit_per_minute}/minute)"

            if capability.rate_limit_per_hour and status.requests_this_hour >= capability.rate_limit_per_hour:
                return True, f"Rate limit exceeded ({capability.rate_limit_per_hour}/hour)"

            if capability.rate_limit_per_day and status.requests_this_day >= capability.rate_limit_per_day:
                return True, f"Rate limit exceeded ({capability.rate_limit_per_day}/day)"

        return False, None

    def record_usage(self, client_id: str, capability_type: CapabilityType) -> None:
        """Record usage of a capability for rate limiting."""
        with self._lock:
            status = self._rate_limits[client_id][capability_type]
            now = datetime.utcnow()

            # Reset windows if expired
            if now - status.minute_window_start > timedelta(minutes=1):
                status.requests_this_minute = 0
                status.minute_window_start = now
            if now - status.hour_window_start > timedelta(hours=1):
                status.requests_this_hour = 0
                status.hour_window_start = now
            if now - status.day_window_start > timedelta(days=1):
                status.requests_this_day = 0
                status.day_window_start = now

            # Increment counters
            status.requests_this_minute += 1
            status.requests_this_hour += 1
            status.requests_this_day += 1

    def get_rate_limit_status(
        self,
        client_id: str,
        capability_type: CapabilityType,
    ) -> Dict[str, Any]:
        """Get current rate limit status for a client and capability."""
        capability = self._capabilities.get(capability_type)
        if not capability:
            return {}

        with self._lock:
            status = self._rate_limits[client_id][capability_type]
            return {
                "requests_this_minute": status.requests_this_minute,
                "requests_this_hour": status.requests_this_hour,
                "requests_this_day": status.requests_this_day,
                "limit_per_minute": capability.rate_limit_per_minute,
                "limit_per_hour": capability.rate_limit_per_hour,
                "limit_per_day": capability.rate_limit_per_day,
            }

    def enable_capability(self, capability_type: CapabilityType) -> bool:
        """Enable a capability."""
        if capability_type in self._capabilities:
            self._capabilities[capability_type].enabled = True
            return True
        return False

    def disable_capability(self, capability_type: CapabilityType) -> bool:
        """Disable a capability."""
        if capability_type in self._capabilities:
            self._capabilities[capability_type].enabled = False
            return True
        return False

    def update_rate_limit(
        self,
        capability_type: CapabilityType,
        per_minute: Optional[int] = None,
        per_hour: Optional[int] = None,
        per_day: Optional[int] = None,
    ) -> bool:
        """Update rate limits for a capability."""
        if capability_type not in self._capabilities:
            return False

        cap = self._capabilities[capability_type]
        if per_minute is not None:
            cap.rate_limit_per_minute = per_minute
        if per_hour is not None:
            cap.rate_limit_per_hour = per_hour
        if per_day is not None:
            cap.rate_limit_per_day = per_day
        return True


# Global registry instance
_registry: Optional[CapabilityRegistry] = None


def get_capability_registry() -> CapabilityRegistry:
    """Get the global capability registry."""
    global _registry
    if _registry is None:
        _registry = CapabilityRegistry()
    return _registry
