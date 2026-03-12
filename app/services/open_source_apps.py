"""Open Source Apps service.

Manages the curated directory of open-source applications
with installation guides and platform information.
"""
import logging
from typing import Any, Optional

from sqlalchemy import cast, func as sa_func, type_coerce
from sqlalchemy.dialects.postgresql import JSONB as JSONB_TYPE
from sqlalchemy.orm import Session

from app.models.open_source_app import OpenSourceApp

logger = logging.getLogger(__name__)


def get_apps(
    db: Session,
    deployment_type: Optional[str] = None,
    difficulty: Optional[str] = None,
    platform: Optional[str] = None,
    sort_by: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Get published apps, optionally filtered.

    sort_by: "popularity" (stars desc), "rating", or None (featured first, then name).
    """
    query = db.query(OpenSourceApp).filter(
        OpenSourceApp.status == "published"
    )

    if deployment_type:
        query = query.filter(OpenSourceApp.deployment_type == deployment_type)
    if difficulty:
        query = query.filter(OpenSourceApp.difficulty == difficulty)

    # SQL-level JSONB platform filtering (uses GIN index)
    if platform:
        query = query.filter(
            OpenSourceApp.platforms.op("@>")(type_coerce([platform], JSONB_TYPE))
        )

    # Sorting
    if sort_by == "popularity":
        query = query.order_by(OpenSourceApp.github_stars.desc().nullslast(), OpenSourceApp.name)
    elif sort_by == "rating":
        query = query.order_by(OpenSourceApp.community_rating.desc().nullslast(), OpenSourceApp.name)
    else:
        query = query.order_by(OpenSourceApp.is_featured.desc(), OpenSourceApp.name)

    apps = query.all()
    return [_app_to_dict(a) for a in apps]


def get_app_by_slug(db: Session, slug: str) -> Optional[OpenSourceApp]:
    """Get a single app by slug."""
    return (
        db.query(OpenSourceApp)
        .filter(OpenSourceApp.slug == slug)
        .first()
    )


def get_directory_stats(db: Session) -> dict[str, Any]:
    """Stats for the directory page."""
    total = (
        db.query(sa_func.count(OpenSourceApp.id))
        .filter(OpenSourceApp.status == "published")
        .scalar()
    ) or 0

    deployment_types = (
        db.query(
            OpenSourceApp.deployment_type,
            sa_func.count(OpenSourceApp.id),
        )
        .filter(OpenSourceApp.status == "published")
        .group_by(OpenSourceApp.deployment_type)
        .all()
    )

    featured = (
        db.query(sa_func.count(OpenSourceApp.id))
        .filter(
            OpenSourceApp.status == "published",
            OpenSourceApp.is_featured.is_(True),
        )
        .scalar()
    ) or 0

    return {
        "total_apps": total,
        "featured_count": featured,
        "deployment_types": [{"type": t, "count": n} for t, n in deployment_types],
    }


def get_apps_by_slugs(db: Session, slugs: list[str]) -> list[dict[str, Any]]:
    """Get published apps matching a list of slugs (for lesson-app integration)."""
    if not slugs:
        return []
    apps = (
        db.query(OpenSourceApp)
        .filter(
            OpenSourceApp.slug.in_(slugs),
            OpenSourceApp.status == "published",
        )
        .all()
    )
    return [_app_to_dict(a) for a in apps]


def _app_to_dict(a: OpenSourceApp) -> dict[str, Any]:
    """Convert app model to dict."""
    return {
        "id": str(a.id),
        "slug": a.slug,
        "name": a.name,
        "description": a.description,
        "github_url": a.github_url,
        "website_url": a.website_url,
        "docs_url": a.docs_url,
        "categories": a.categories or [],
        "tags": a.tags or [],
        "sectors": a.sectors or [],
        "license_type": a.license_type,
        "deployment_type": a.deployment_type,
        "platforms": a.platforms or [],
        "difficulty": a.difficulty,
        "pricing_model": a.pricing_model,
        "is_featured": a.is_featured,
        "github_stars": a.github_stars,
        "community_rating": a.community_rating,
        "last_verified_at": a.last_verified_at.isoformat() if a.last_verified_at else None,
    }
