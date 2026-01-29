"""
Product Context Utilities.

This module provides utilities for accessing the current product and edition
context throughout the application. It includes FastAPI dependencies and
helper functions for feature flag checking.
"""

from typing import Optional
from fastapi import Request

from app.products.config import Product, Edition, FeatureFlags
from app.products.registry import (
    ProductRegistry,
    EditionRegistry,
    get_active_edition,
)


# Default product when none is specified
DEFAULT_PRODUCT_ID = "ai_toolkit"


def get_current_product(request: Optional[Request] = None) -> Product:
    """
    Get the current product based on request context.

    For now, this returns AI Toolkit as the default product.
    In the future, this could be determined by:
    - Subdomain (toolkit.example.com vs audio.example.com)
    - URL path prefix (/toolkit/* vs /audio/*)
    - Request header
    - User preference

    Args:
        request: Optional FastAPI request object

    Returns:
        Current Product instance
    """
    # Future: Implement product detection logic based on request
    # For now, return the default product
    product = ProductRegistry.get(DEFAULT_PRODUCT_ID)
    if product is None:
        raise RuntimeError(
            f"Default product '{DEFAULT_PRODUCT_ID}' not registered. "
            "Ensure register_all_products() is called during startup."
        )
    return product


def get_current_edition(request: Optional[Request] = None) -> Edition:
    """
    Get the current active edition for the current product.

    Args:
        request: Optional FastAPI request object

    Returns:
        Current Edition instance
    """
    product = get_current_product(request)
    edition = get_active_edition(product.id)
    if edition is None:
        raise RuntimeError(
            f"No active edition for product '{product.id}'. "
            "Ensure editions are registered during startup."
        )
    return edition


def get_feature_flags(request: Optional[Request] = None) -> FeatureFlags:
    """
    Get the feature flags for the current edition.

    Args:
        request: Optional FastAPI request object

    Returns:
        FeatureFlags instance for current edition
    """
    edition = get_current_edition(request)
    return edition.feature_flags


def is_feature_enabled(feature_name: str, request: Optional[Request] = None) -> bool:
    """
    Check if a specific feature is enabled in the current edition.

    Args:
        feature_name: Name of the feature flag (e.g., "rag_enabled")
        request: Optional FastAPI request object

    Returns:
        True if feature is enabled, False otherwise

    Raises:
        AttributeError: If feature_name is not a valid feature flag
    """
    flags = get_feature_flags(request)
    return getattr(flags, feature_name)


# Feature-specific convenience functions
def is_rag_enabled(request: Optional[Request] = None) -> bool:
    """Check if RAG is enabled."""
    return is_feature_enabled("rag_enabled", request)


def is_discovery_enabled(request: Optional[Request] = None) -> bool:
    """Check if discovery pipeline is enabled."""
    return is_feature_enabled("discovery_enabled", request)


def is_clusters_enabled(request: Optional[Request] = None) -> bool:
    """Check if clusters feature is enabled."""
    return is_feature_enabled("clusters_enabled", request)


def is_strategy_enabled(request: Optional[Request] = None) -> bool:
    """Check if strategy builder is enabled."""
    return is_feature_enabled("strategy_enabled", request)


def is_foundations_enabled(request: Optional[Request] = None) -> bool:
    """Check if foundations are enabled."""
    return is_feature_enabled("foundations_enabled", request)


def is_playbooks_enabled(request: Optional[Request] = None) -> bool:
    """Check if playbooks are enabled."""
    return is_feature_enabled("playbooks_enabled", request)


def is_recommendations_enabled(request: Optional[Request] = None) -> bool:
    """Check if recommendations are enabled."""
    return is_feature_enabled("recommendations_enabled", request)


def is_reviews_enabled(request: Optional[Request] = None) -> bool:
    """Check if reviews are enabled."""
    return is_feature_enabled("reviews_enabled", request)


def is_browse_enabled(request: Optional[Request] = None) -> bool:
    """Check if browse is enabled."""
    return is_feature_enabled("browse_enabled", request)


def is_sources_enabled(request: Optional[Request] = None) -> bool:
    """Check if sources are enabled."""
    return is_feature_enabled("sources_enabled", request)


def is_admin_dashboard_enabled(request: Optional[Request] = None) -> bool:
    """Check if admin dashboard is enabled."""
    return is_feature_enabled("admin_dashboard", request)


# FastAPI dependency for injecting product context
async def product_context(request: Request) -> dict:
    """
    FastAPI dependency that provides product context to templates.

    This can be used in route handlers to get product information:

        @router.get("/")
        async def home(ctx: dict = Depends(product_context)):
            return templates.TemplateResponse("home.html", {
                "request": request,
                "product": ctx["product"],
                "edition": ctx["edition"],
                "features": ctx["features"],
            })

    Returns:
        Dict with product, edition, and feature flags
    """
    product = get_current_product(request)
    edition = get_current_edition(request)

    return {
        "product": product,
        "edition": edition,
        "features": edition.feature_flags,
        "product_name": product.name,
        "edition_name": edition.display_name,
        "is_sealed": edition.is_sealed,
    }
