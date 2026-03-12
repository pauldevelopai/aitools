"""Intelligence Feed router — curated AI developments and updates."""
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.db import get_db
from app.dependencies import get_current_user, require_auth
from app.models.auth import User
from app.products.guards import require_feature
from app.templates_engine import templates
from app.services.intelligence_feed import (
    get_feed,
    get_feed_item,
    get_categories_with_counts,
    mark_as_read,
)

router = APIRouter(prefix="/intelligence-feed", tags=["intelligence-feed"])


@router.get("/", response_class=HTMLResponse)
async def feed_listing(
    request: Request,
    category: Optional[str] = None,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("intelligence_feed")),
):
    """Intelligence feed listing with category filters."""
    user_id = user.id if user else None
    feed_data = get_feed(db, user_id=user_id, category=category)
    categories = get_categories_with_counts(db)

    requires_login = user is None

    return templates.TemplateResponse(
        "intelligence_feed/feed.html",
        {
            "request": request,
            "user": user,
            "title": "Intelligence Feed",
            "feed_data": feed_data,
            "categories": categories,
            "active_category": category,
            "requires_login": requires_login,
            "feature_name": "intelligence feed",
            "feature_description": "Stay current on AI developments that matter to your organisation.",
        },
    )


@router.get("/{slug}", response_class=HTMLResponse)
async def feed_item_detail(
    request: Request,
    slug: str,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("intelligence_feed")),
):
    """Single feed item detail page."""
    item = get_feed_item(db, slug)
    if not item:
        raise HTTPException(status_code=404, detail="Feed item not found")

    return templates.TemplateResponse(
        "intelligence_feed/item.html",
        {
            "request": request,
            "user": user,
            "title": item.title,
            "item": item,
        },
    )


@router.post("/{slug}/read")
async def mark_feed_read(
    slug: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Mark a feed item as read (JSON endpoint)."""
    item = get_feed_item(db, slug)
    if not item:
        raise HTTPException(status_code=404, detail="Feed item not found")

    result = mark_as_read(db, user.id, item.id)
    return JSONResponse({"marked": result})
