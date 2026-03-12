"""Data Asset Registry service.

Manages data asset registration, discovery, and licensing inquiries.
"""
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.models.data_registry import DataAsset, LicenseInquiry

logger = logging.getLogger(__name__)


def _slugify(text: str) -> str:
    """Generate a URL-safe slug from text."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug[:80]


def get_registry(
    db: Session,
    asset_type: Optional[str] = None,
    is_licensable: Optional[bool] = None,
    sector: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Get active data assets, optionally filtered."""
    query = db.query(DataAsset).filter(DataAsset.status == "active")

    if asset_type:
        query = query.filter(DataAsset.asset_type == asset_type)
    if is_licensable is not None:
        query = query.filter(DataAsset.is_licensable == is_licensable)
    if sector:
        # Filter by JSONB sector array contains
        query = query.filter(DataAsset.sectors.contains([sector]))

    assets = (
        query
        .order_by(DataAsset.created_at.desc())
        .all()
    )

    return [_asset_to_dict(a) for a in assets]


def get_asset_by_slug(db: Session, slug: str) -> Optional[DataAsset]:
    """Get a single asset by slug."""
    return (
        db.query(DataAsset)
        .filter(DataAsset.slug == slug)
        .first()
    )


def get_user_assets(db: Session, user_id) -> list[dict[str, Any]]:
    """Get all assets created by a user."""
    assets = (
        db.query(DataAsset)
        .filter(DataAsset.created_by == user_id)
        .order_by(DataAsset.created_at.desc())
        .all()
    )

    result = []
    for a in assets:
        d = _asset_to_dict(a)
        # Add inquiry count
        inquiry_count = (
            db.query(sa_func.count(LicenseInquiry.id))
            .filter(LicenseInquiry.asset_id == a.id)
            .scalar()
        ) or 0
        d["inquiry_count"] = inquiry_count
        result.append(d)

    return result


def create_asset(db: Session, user_id, **kwargs) -> DataAsset:
    """Create a new data asset, auto-generating slug."""
    name = kwargs.get("name", "untitled")
    base_slug = _slugify(name)
    slug = base_slug
    counter = 1
    while db.query(DataAsset).filter(DataAsset.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    asset = DataAsset(
        slug=slug,
        created_by=user_id,
        **kwargs,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def update_asset(db: Session, asset_id, user_id, **kwargs) -> Optional[DataAsset]:
    """Update an asset (only by creator)."""
    asset = db.query(DataAsset).filter(
        DataAsset.id == asset_id,
        DataAsset.created_by == user_id,
    ).first()

    if not asset:
        return None

    for key, value in kwargs.items():
        if hasattr(asset, key) and key not in ("id", "slug", "created_by", "created_at"):
            setattr(asset, key, value)

    db.commit()
    db.refresh(asset)
    return asset


def submit_inquiry(db: Session, user_id, asset_id, message: str) -> dict:
    """Submit a licensing inquiry for a data asset."""
    asset = db.query(DataAsset).filter(DataAsset.id == asset_id).first()
    if not asset:
        return {"error": "Asset not found"}

    if not asset.is_licensable:
        return {"error": "This asset is not available for licensing"}

    # Check for existing inquiry
    existing = (
        db.query(LicenseInquiry)
        .filter(
            LicenseInquiry.asset_id == asset_id,
            LicenseInquiry.requester_id == user_id,
            LicenseInquiry.status == "pending",
        )
        .first()
    )
    if existing:
        return {"error": "You already have a pending inquiry for this asset"}

    inquiry = LicenseInquiry(
        asset_id=asset_id,
        requester_id=user_id,
        message=message,
    )
    db.add(inquiry)
    db.commit()
    db.refresh(inquiry)

    return {"inquiry_id": str(inquiry.id), "status": "pending"}


def get_registry_stats(db: Session) -> dict[str, Any]:
    """Registry-wide statistics."""
    total = (
        db.query(sa_func.count(DataAsset.id))
        .filter(DataAsset.status == "active")
        .scalar()
    ) or 0

    by_type = (
        db.query(
            DataAsset.asset_type,
            sa_func.count(DataAsset.id),
        )
        .filter(DataAsset.status == "active")
        .group_by(DataAsset.asset_type)
        .all()
    )

    licensable = (
        db.query(sa_func.count(DataAsset.id))
        .filter(DataAsset.status == "active", DataAsset.is_licensable.is_(True))
        .scalar()
    ) or 0

    return {
        "total_assets": total,
        "by_type": [{"type": t, "count": c} for t, c in by_type],
        "licensable_count": licensable,
    }


def _asset_to_dict(a: DataAsset) -> dict[str, Any]:
    """Convert asset model to dict."""
    return {
        "id": str(a.id),
        "name": a.name,
        "slug": a.slug,
        "description": a.description,
        "asset_type": a.asset_type,
        "data_format": a.data_format,
        "record_count": a.record_count,
        "date_range_start": a.date_range_start.isoformat() if a.date_range_start else None,
        "date_range_end": a.date_range_end.isoformat() if a.date_range_end else None,
        "languages": a.languages or [],
        "sectors": a.sectors or [],
        "tags": a.tags or [],
        "classification": a.classification,
        "is_licensable": a.is_licensable,
        "licensing_terms": a.licensing_terms,
        "contact_email": a.contact_email,
        "status": a.status,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }
