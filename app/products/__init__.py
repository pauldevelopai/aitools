"""
Products, Editions, and Version Sealing Architecture.

This module provides the foundational architecture for managing:
- Products: Distinct apps sharing infrastructure (AI Toolkit, AI Audio, Letter+)
- Editions: Different versions of the same product (Toolkit V1, V2, etc.)
- Sealing: Mechanism to freeze versions so new versions don't affect sealed ones

Usage:
    from app.products import get_product, get_edition, get_active_edition
    from app.products import ProductRegistry, EditionRegistry

    # Get the current active product and edition
    toolkit = get_product("ai_toolkit")
    current_edition = get_active_edition("ai_toolkit")

    # Check if an edition is sealed
    v1 = get_edition("ai_toolkit", "v1")
    if v1.is_sealed:
        print("V1 is frozen - no new features")
"""

from app.products.config import (
    Product,
    Edition,
    FeatureFlags,
    Branding,
    NavigationItem,
    ContentScope,
)
from app.products.registry import (
    ProductRegistry,
    EditionRegistry,
    get_product,
    get_edition,
    get_active_edition,
    list_products,
    list_editions,
    create_new_edition,
)
from app.products.context import (
    get_current_product,
    get_current_edition,
    get_feature_flags,
    is_feature_enabled,
    product_context,
    # Feature-specific helpers
    is_rag_enabled,
    is_discovery_enabled,
    is_clusters_enabled,
    is_strategy_enabled,
    is_foundations_enabled,
    is_playbooks_enabled,
    is_recommendations_enabled,
    is_reviews_enabled,
    is_browse_enabled,
    is_sources_enabled,
    is_admin_dashboard_enabled,
)

__all__ = [
    # Models
    "Product",
    "Edition",
    "FeatureFlags",
    "Branding",
    "NavigationItem",
    "ContentScope",
    # Registry
    "ProductRegistry",
    "EditionRegistry",
    # Registry helper functions
    "get_product",
    "get_edition",
    "get_active_edition",
    "list_products",
    "list_editions",
    "create_new_edition",
    # Context helpers
    "get_current_product",
    "get_current_edition",
    "get_feature_flags",
    "is_feature_enabled",
    "product_context",
    # Feature-specific helpers
    "is_rag_enabled",
    "is_discovery_enabled",
    "is_clusters_enabled",
    "is_strategy_enabled",
    "is_foundations_enabled",
    "is_playbooks_enabled",
    "is_recommendations_enabled",
    "is_reviews_enabled",
    "is_browse_enabled",
    "is_sources_enabled",
    "is_admin_dashboard_enabled",
]
