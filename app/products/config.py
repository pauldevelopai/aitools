"""
Product and Edition Configuration Models.

This module defines the core data structures for products, editions,
and their associated configuration including branding, navigation,
and feature flags.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from enum import Enum


def utc_now() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class ContentScope(Enum):
    """Defines the default content scope for a product."""
    TOOLS = "tools"           # AI tools and productivity
    AUDIO = "audio"           # Audio production and editing
    WRITING = "writing"       # Writing and letter composition
    GENERAL = "general"       # General purpose


@dataclass(frozen=True)
class Branding:
    """
    Product branding configuration.

    Attributes:
        logo_text: Text displayed as logo (e.g., "AI Toolkit")
        logo_path: Optional path to logo image asset
        primary_color: Primary brand color (hex)
        secondary_color: Secondary brand color (hex)
        accent_color: Accent color for highlights (hex)
    """
    logo_text: str
    logo_path: Optional[str] = None
    primary_color: str = "#3B82F6"   # Blue
    secondary_color: str = "#1E40AF"  # Dark blue
    accent_color: str = "#10B981"     # Green


@dataclass(frozen=True)
class NavigationItem:
    """
    A single navigation menu item.

    Attributes:
        label: Display text for the nav item
        route: URL path or route name
        icon: Optional icon name (for icon libraries)
        requires_auth: Whether this item requires authentication
        requires_admin: Whether this item requires admin privileges
    """
    label: str
    route: str
    icon: Optional[str] = None
    requires_auth: bool = False
    requires_admin: bool = False


@dataclass
class FeatureFlags:
    """
    Feature flags for controlling functionality in editions.

    Each flag controls a specific feature that can be enabled or disabled
    per edition. This allows different editions to have different capabilities.

    Attributes:
        rag_enabled: RAG (Retrieval Augmented Generation) chat
        discovery_enabled: Tool discovery pipeline
        clusters_enabled: Tool clustering feature
        strategy_enabled: Strategy builder
        foundations_enabled: Learning foundations/materials
        playbooks_enabled: Tool playbooks/guides
        recommendations_enabled: Personalized recommendations
        reviews_enabled: User reviews system
        browse_enabled: Document browsing
        sources_enabled: Citation sources
        admin_dashboard: Admin dashboard access
    """
    # Core features
    rag_enabled: bool = True
    discovery_enabled: bool = True

    # Tool organization
    clusters_enabled: bool = True
    strategy_enabled: bool = True

    # Learning content
    foundations_enabled: bool = True
    playbooks_enabled: bool = True

    # Personalization
    recommendations_enabled: bool = True
    reviews_enabled: bool = True

    # Content access
    browse_enabled: bool = True
    sources_enabled: bool = True

    # Administration
    admin_dashboard: bool = True

    def clone(self, **overrides) -> "FeatureFlags":
        """Create a copy with optional overrides."""
        current = {
            "rag_enabled": self.rag_enabled,
            "discovery_enabled": self.discovery_enabled,
            "clusters_enabled": self.clusters_enabled,
            "strategy_enabled": self.strategy_enabled,
            "foundations_enabled": self.foundations_enabled,
            "playbooks_enabled": self.playbooks_enabled,
            "recommendations_enabled": self.recommendations_enabled,
            "reviews_enabled": self.reviews_enabled,
            "browse_enabled": self.browse_enabled,
            "sources_enabled": self.sources_enabled,
            "admin_dashboard": self.admin_dashboard,
        }
        current.update(overrides)
        return FeatureFlags(**current)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "rag_enabled": self.rag_enabled,
            "discovery_enabled": self.discovery_enabled,
            "clusters_enabled": self.clusters_enabled,
            "strategy_enabled": self.strategy_enabled,
            "foundations_enabled": self.foundations_enabled,
            "playbooks_enabled": self.playbooks_enabled,
            "recommendations_enabled": self.recommendations_enabled,
            "reviews_enabled": self.reviews_enabled,
            "browse_enabled": self.browse_enabled,
            "sources_enabled": self.sources_enabled,
            "admin_dashboard": self.admin_dashboard,
        }


@dataclass
class Product:
    """
    A product definition.

    Products are distinct applications that share infrastructure but
    present as separate apps to users. Examples: AI Toolkit, AI Audio, Letter+

    Attributes:
        id: Unique identifier (e.g., "ai_toolkit")
        name: Display name (e.g., "AI Toolkit")
        description: Short product description
        branding: Branding configuration
        navigation: List of navigation items
        content_scope: Default content scope
        is_active: Whether this product is currently active/available
    """
    id: str
    name: str
    description: str
    branding: Branding
    navigation: list[NavigationItem] = field(default_factory=list)
    content_scope: ContentScope = ContentScope.GENERAL
    is_active: bool = True

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, Product):
            return self.id == other.id
        return False


@dataclass
class Edition:
    """
    An edition/version of a product.

    Editions represent different versions of the same product. They share
    the product identity but can have different features and capabilities.

    Version Sealing:
    - When an edition is sealed, it becomes read-only
    - No new features are added to sealed editions
    - Sealed editions serve as historical references

    Attributes:
        product_id: ID of the parent product
        version: Version label (e.g., "v1", "v2")
        display_name: Human-readable name (e.g., "Toolkit V2")
        feature_flags: Features enabled in this edition
        is_sealed: Whether this edition is sealed (frozen)
        is_active: Whether this is the active/current edition
        sealed_at: Datetime when the edition was sealed
        sealed_reason: Reason for sealing (documentation)
        git_reference: Optional git commit/tag reference for sealed editions
        created_at: When this edition was defined
        description: Optional description of this edition
    """
    product_id: str
    version: str
    display_name: str
    feature_flags: FeatureFlags
    is_sealed: bool = False
    is_active: bool = True
    sealed_at: Optional[datetime] = None
    sealed_reason: Optional[str] = None
    git_reference: Optional[str] = None
    created_at: datetime = field(default_factory=utc_now)
    description: Optional[str] = None

    @property
    def edition_id(self) -> str:
        """Unique identifier combining product and version."""
        return f"{self.product_id}:{self.version}"

    def __hash__(self):
        return hash(self.edition_id)

    def __eq__(self, other):
        if isinstance(other, Edition):
            return self.edition_id == other.edition_id
        return False

    def seal(self, reason: Optional[str] = None) -> "Edition":
        """
        Seal this edition, making it read-only.

        Args:
            reason: Optional reason for sealing

        Returns:
            Self for chaining

        Raises:
            ValueError: If already sealed
        """
        if self.is_sealed:
            raise ValueError(f"Edition {self.edition_id} is already sealed")

        self.is_sealed = True
        self.is_active = False
        self.sealed_at = utc_now()
        self.sealed_reason = reason
        return self

    def clone_for_new_version(
        self,
        new_version: str,
        display_name: Optional[str] = None,
        feature_overrides: Optional[dict] = None,
    ) -> "Edition":
        """
        Create a new edition based on this one.

        This is the primary mechanism for creating new versions:
        1. Clone an existing edition's configuration
        2. Assign a new version label
        3. Optionally override feature flags

        Args:
            new_version: Version label for new edition (e.g., "v3")
            display_name: Optional custom display name
            feature_overrides: Optional dict of feature flag overrides

        Returns:
            New Edition instance (not yet registered)
        """
        new_flags = self.feature_flags.clone(**(feature_overrides or {}))

        return Edition(
            product_id=self.product_id,
            version=new_version,
            display_name=display_name or f"{self.product_id.replace('_', ' ').title()} {new_version.upper()}",
            feature_flags=new_flags,
            is_sealed=False,
            is_active=True,
            description=f"Cloned from {self.edition_id}",
        )
