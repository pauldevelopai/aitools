"""AI Legal Framework public routes."""
from typing import Optional
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.auth import User
from app.dependencies import get_current_user
from app.db import get_db
from app.models.governance import ContentItem
from app.templates_engine import templates


router = APIRouter(prefix="/legal-framework", tags=["legal_framework"])


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def legal_framework_index(
    request: Request,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List published AI Legal Framework content."""
    items = (
        db.query(ContentItem)
        .filter(
            ContentItem.section == "legal_framework",
            ContentItem.status == "published",
        )
        .order_by(desc(ContentItem.published_at))
        .all()
    )

    return templates.TemplateResponse(
        "legal_framework/index.html",
        {
            "request": request,
            "user": user,
            "items": items,
        }
    )


@router.get("/{slug}", response_class=HTMLResponse)
async def legal_framework_detail(
    request: Request,
    slug: str,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """View a single AI Legal Framework item."""
    item = (
        db.query(ContentItem)
        .filter(
            ContentItem.slug == slug,
            ContentItem.section == "legal_framework",
            ContentItem.status == "published",
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")

    return templates.TemplateResponse(
        "legal_framework/detail.html",
        {
            "request": request,
            "user": user,
            "item": item,
        }
    )
