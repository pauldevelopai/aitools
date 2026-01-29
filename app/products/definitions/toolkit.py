"""
AI Toolkit Product Definition.

This is the primary product in the system. It defines:
- AI Toolkit product configuration
- Toolkit V1 (sealed, historical edition)
- Toolkit V2 (current, active edition)
"""

from datetime import datetime
from app.products.config import (
    Product,
    Edition,
    FeatureFlags,
    Branding,
    NavigationItem,
    ContentScope,
)
from app.products.registry import ProductRegistry, EditionRegistry


# =============================================================================
# PRODUCT DEFINITION
# =============================================================================

AI_TOOLKIT_PRODUCT = Product(
    id="ai_toolkit",
    name="AI Toolkit",
    description="The AI Editorial Toolkit for discovering and mastering AI tools",
    branding=Branding(
        logo_text="AI Toolkit",
        logo_path=None,  # Uses text-based logo
        primary_color="#3B82F6",    # Blue
        secondary_color="#1E40AF",  # Dark blue
        accent_color="#10B981",     # Green
    ),
    navigation=[
        NavigationItem(
            label="Tools",
            route="/tools",
            icon="wrench",
            requires_auth=False,
        ),
        NavigationItem(
            label="Tool Finder",
            route="/toolkit",
            icon="search",
            requires_auth=True,
        ),
        NavigationItem(
            label="CDI",
            route="/tools/cdi",
            icon="chart",
            requires_auth=False,
        ),
        NavigationItem(
            label="Clusters",
            route="/clusters",
            icon="grid",
            requires_auth=False,
        ),
        NavigationItem(
            label="Foundations",
            route="/foundations",
            icon="book",
            requires_auth=False,
        ),
        NavigationItem(
            label="Sources",
            route="/sources",
            icon="link",
            requires_auth=False,
        ),
        NavigationItem(
            label="Browse",
            route="/browse",
            icon="folder",
            requires_auth=True,
        ),
        NavigationItem(
            label="History",
            route="/toolkit/history",
            icon="clock",
            requires_auth=True,
        ),
        NavigationItem(
            label="Strategy",
            route="/strategy",
            icon="target",
            requires_auth=True,
        ),
    ],
    content_scope=ContentScope.TOOLS,
    is_active=True,
)


# =============================================================================
# EDITION DEFINITIONS
# =============================================================================

# -----------------------------------------------------------------------------
# TOOLKIT V1 - Sealed Historical Edition
# -----------------------------------------------------------------------------
# This edition represents the state of the toolkit at a specific point in time.
# It is sealed and serves as a historical reference. The git reference points
# to the commit where V1 was finalized.

TOOLKIT_V1_FEATURES = FeatureFlags(
    # Core features available in V1
    rag_enabled=True,
    discovery_enabled=False,  # Discovery was not in V1
    clusters_enabled=True,
    strategy_enabled=False,   # Strategy was not in V1
    foundations_enabled=True,
    playbooks_enabled=False,  # Playbooks were not in V1
    recommendations_enabled=False,  # Recommendations were not in V1
    reviews_enabled=False,    # Reviews were not in V1
    browse_enabled=True,
    sources_enabled=True,
    admin_dashboard=True,
)

TOOLKIT_V1_EDITION = Edition(
    product_id="ai_toolkit",
    version="v1",
    display_name="Toolkit V1",
    feature_flags=TOOLKIT_V1_FEATURES,
    is_sealed=True,
    is_active=False,
    sealed_at=datetime(2025, 1, 15, 0, 0, 0),  # Approximate seal date
    sealed_reason="V1 finalized before V2 development began",
    git_reference="a794966e77bcf1ef16ee3d93ed2a3fc5779b74a6",
    created_at=datetime(2024, 12, 1, 0, 0, 0),  # Approximate creation date
    description=(
        "Initial version of AI Toolkit with core RAG functionality, "
        "cluster organization, foundations, and document browsing. "
        "This version predates the discovery pipeline and strategy features."
    ),
)


# -----------------------------------------------------------------------------
# TOOLKIT V2 - Current Active Edition
# -----------------------------------------------------------------------------
# This is the current working version with all features enabled.
# It is not sealed and continues to receive updates.

TOOLKIT_V2_FEATURES = FeatureFlags(
    # All features enabled in V2
    rag_enabled=True,
    discovery_enabled=True,
    clusters_enabled=True,
    strategy_enabled=True,
    foundations_enabled=True,
    playbooks_enabled=True,
    recommendations_enabled=True,
    reviews_enabled=True,
    browse_enabled=True,
    sources_enabled=True,
    admin_dashboard=True,
)

TOOLKIT_V2_EDITION = Edition(
    product_id="ai_toolkit",
    version="v2",
    display_name="Toolkit V2",
    feature_flags=TOOLKIT_V2_FEATURES,
    is_sealed=False,
    is_active=True,
    sealed_at=None,
    sealed_reason=None,
    git_reference=None,  # Not sealed, no fixed reference
    created_at=datetime(2025, 1, 1, 0, 0, 0),
    description=(
        "Current version of AI Toolkit with full feature set including "
        "discovery pipeline, strategy builder, playbooks, recommendations, "
        "and user reviews. This is the active development version."
    ),
)


# =============================================================================
# REGISTRATION
# =============================================================================

def register_toolkit() -> None:
    """
    Register the AI Toolkit product and its editions.

    This function should be called during application startup.
    """
    # Register the product first
    ProductRegistry.register(AI_TOOLKIT_PRODUCT)

    # Register editions (V1 sealed, then V2 active)
    EditionRegistry.register(TOOLKIT_V1_EDITION)
    EditionRegistry.register(TOOLKIT_V2_EDITION)
