"""Intelligence Feed service.

Manages the curated intelligence feed of AI developments,
regulatory updates, security alerts, and platform news.
"""
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.models.intelligence_feed import FeedItem, UserFeedRead

logger = logging.getLogger(__name__)


def _slugify(text: str) -> str:
    """Generate a URL-safe slug from text."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug[:80]


def get_feed(
    db: Session,
    user_id=None,
    category: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """Get paginated feed items, optionally filtered by category.

    Returns:
        {"items": [...], "total": int, "has_more": bool}
    """
    now = datetime.now(timezone.utc)

    query = (
        db.query(FeedItem)
        .filter(
            FeedItem.status == "published",
            FeedItem.published_at <= now,
        )
    )

    # Exclude expired items
    query = query.filter(
        (FeedItem.expires_at.is_(None)) | (FeedItem.expires_at > now)
    )

    if category:
        query = query.filter(FeedItem.feed_category == category)

    total = query.count()
    items = (
        query
        .order_by(FeedItem.published_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    # Get read status if user is logged in
    read_ids = set()
    if user_id:
        reads = (
            db.query(UserFeedRead.feed_item_id)
            .filter(UserFeedRead.user_id == user_id)
            .all()
        )
        read_ids = {r[0] for r in reads}

    items_list = [
        {
            "id": str(item.id),
            "title": item.title,
            "slug": item.slug,
            "summary": item.summary,
            "category": item.feed_category,
            "source_url": item.source_url,
            "source_name": item.source_name,
            "jurisdiction": item.jurisdiction,
            "sectors": item.sectors or [],
            "tags": item.tags or [],
            "published_at": item.published_at.isoformat() if item.published_at else None,
            "is_read": item.id in read_ids,
        }
        for item in items
    ]

    return {
        "feed_items": items_list,
        "total": total,
        "has_more": (offset + limit) < total,
    }


def get_feed_item(db: Session, slug: str) -> Optional[FeedItem]:
    """Get a single feed item by slug."""
    return (
        db.query(FeedItem)
        .filter(FeedItem.slug == slug)
        .first()
    )


def get_categories_with_counts(db: Session) -> list[dict]:
    """Get category breakdown for sidebar/filter."""
    now = datetime.now(timezone.utc)

    counts = (
        db.query(
            FeedItem.feed_category,
            sa_func.count(FeedItem.id),
        )
        .filter(
            FeedItem.status == "published",
            FeedItem.published_at <= now,
            (FeedItem.expires_at.is_(None)) | (FeedItem.expires_at > now),
        )
        .group_by(FeedItem.feed_category)
        .order_by(sa_func.count(FeedItem.id).desc())
        .all()
    )

    return [
        {"category": cat, "count": cnt}
        for cat, cnt in counts
    ]


def mark_as_read(db: Session, user_id, feed_item_id) -> bool:
    """Mark a feed item as read by a user."""
    existing = (
        db.query(UserFeedRead)
        .filter(
            UserFeedRead.user_id == user_id,
            UserFeedRead.feed_item_id == feed_item_id,
        )
        .first()
    )
    if existing:
        return False  # Already read

    read_record = UserFeedRead(
        user_id=user_id,
        feed_item_id=feed_item_id,
    )
    db.add(read_record)
    db.commit()
    return True


def create_feed_item(db: Session, **kwargs) -> FeedItem:
    """Create a new feed item (for admin or brain creation)."""
    # Auto-generate slug if not provided
    if "slug" not in kwargs:
        title = kwargs.get("title", "untitled")
        base_slug = _slugify(title)
        slug = base_slug
        counter = 1
        while db.query(FeedItem).filter(FeedItem.slug == slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1
        kwargs["slug"] = slug

    item = FeedItem(**kwargs)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
