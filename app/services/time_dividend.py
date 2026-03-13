"""Time Dividend tracking service.

Tracks hours saved per tool and reinvestment allocation.
"""
import logging
from typing import Any, Optional
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.models.enhancements import TimeDividendEntry

logger = logging.getLogger(__name__)

REINVESTMENT_CATEGORIES = [
    {"key": "investigation", "label": "Investigation & Verification", "color": "blue"},
    {"key": "community", "label": "Community Engagement", "color": "green"},
    {"key": "product", "label": "Product Development", "color": "purple"},
    {"key": "learning", "label": "Learning & Upskilling", "color": "amber"},
]


def add_entry(
    db: Session,
    user_id: str,
    tool_slug: str,
    hours_saved_weekly: float,
    reinvestment_category: Optional[str] = None,
    notes: Optional[str] = None,
) -> TimeDividendEntry:
    """Add or update a time dividend entry for a tool."""
    existing = db.query(TimeDividendEntry).filter(
        TimeDividendEntry.user_id == user_id,
        TimeDividendEntry.tool_slug == tool_slug,
    ).first()

    if existing:
        existing.hours_saved_weekly = hours_saved_weekly
        existing.reinvestment_category = reinvestment_category
        existing.notes = notes
        db.commit()
        db.refresh(existing)
        return existing

    entry = TimeDividendEntry(
        user_id=user_id,
        tool_slug=tool_slug,
        hours_saved_weekly=hours_saved_weekly,
        reinvestment_category=reinvestment_category,
        notes=notes,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_user_entries(db: Session, user_id: str) -> list[TimeDividendEntry]:
    """Get all time dividend entries for a user."""
    return db.query(TimeDividendEntry).filter(
        TimeDividendEntry.user_id == user_id
    ).order_by(TimeDividendEntry.updated_at.desc()).all()


def get_user_summary(db: Session, user_id: str) -> dict[str, Any]:
    """Get summary statistics for a user's time dividend."""
    entries = get_user_entries(db, user_id)

    if not entries:
        return {
            "total_hours_weekly": 0,
            "total_hours_monthly": 0,
            "total_hours_yearly": 0,
            "tool_count": 0,
            "by_category": {},
            "entries": [],
        }

    total = sum(e.hours_saved_weekly for e in entries)
    by_category: dict[str, float] = {}
    for e in entries:
        cat = e.reinvestment_category or "unallocated"
        by_category[cat] = by_category.get(cat, 0) + e.hours_saved_weekly

    return {
        "total_hours_weekly": round(total, 1),
        "total_hours_monthly": round(total * 4.33, 1),
        "total_hours_yearly": round(total * 52, 1),
        "tool_count": len(entries),
        "by_category": by_category,
        "entries": entries,
    }


def remove_entry(db: Session, user_id: str, tool_slug: str) -> bool:
    """Remove a time dividend entry."""
    entry = db.query(TimeDividendEntry).filter(
        TimeDividendEntry.user_id == user_id,
        TimeDividendEntry.tool_slug == tool_slug,
    ).first()
    if entry:
        db.delete(entry)
        db.commit()
        return True
    return False
