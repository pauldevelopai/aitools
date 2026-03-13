"""Time Dividend Tracker router — track hours saved and reinvestment."""
from typing import Optional
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.auth import User
from app.dependencies import get_current_user, require_auth
from app.templates_engine import templates
from app.products.guards import require_time_dividend
from app.services.time_dividend import (
    REINVESTMENT_CATEGORIES, add_entry, get_user_entries,
    get_user_summary, remove_entry
)
from app.services.kit_loader import get_free_tools

router = APIRouter(prefix="/time-dividend", tags=["time-dividend"])


class AddEntryRequest(BaseModel):
    tool_slug: str
    hours_saved_weekly: float
    reinvestment_category: Optional[str] = None
    notes: Optional[str] = None


class RemoveEntryRequest(BaseModel):
    tool_slug: str


@router.get("/", response_class=HTMLResponse)
async def time_dividend_dashboard(
    request: Request,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_time_dividend()),
):
    """Dashboard: summary stats, per-tool breakdown, reinvestment distribution."""
    tools = get_free_tools()
    summary = {}
    entries = []

    if user:
        summary = get_user_summary(db, user.id)
        entries = get_user_entries(db, user.id)

    requires_login = user is None

    # Build tool name lookup
    tool_map = {t.get("slug", ""): t.get("name", "") for t in tools}

    # Attach tool names to entries for display
    entry_list = []
    tracked_slugs = set()
    for e in entries:
        tracked_slugs.add(e.tool_slug)
        entry_list.append({
            "tool_slug": e.tool_slug,
            "tool_name": tool_map.get(e.tool_slug, e.tool_slug),
            "hours_saved_weekly": e.hours_saved_weekly,
            "reinvestment_category": e.reinvestment_category,
            "notes": e.notes,
        })

    # Available tools (not yet tracked) for dropdown
    available_tools = [
        {"slug": t.get("slug", ""), "name": t.get("name", "")}
        for t in tools
        if t.get("slug", "") not in tracked_slugs
    ]

    return templates.TemplateResponse(
        "time_dividend/dashboard.html",
        {
            "request": request,
            "user": user,
            "title": "Time Dividend Tracker",
            "summary": summary,
            "entries": entry_list,
            "available_tools": available_tools,
            "categories": REINVESTMENT_CATEGORIES,
            "tool_map": tool_map,
            "requires_login": requires_login,
            "feature_name": "Time Dividend Tracker",
            "feature_description": "Track the hours you save with AI tools and decide how to reinvest that time.",
        },
    )


@router.post("/api/add", response_class=JSONResponse)
async def time_dividend_add(
    body: AddEntryRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    _: None = Depends(require_time_dividend()),
):
    """Add or update a time dividend entry."""
    entry = add_entry(
        db,
        user_id=user.id,
        tool_slug=body.tool_slug,
        hours_saved_weekly=body.hours_saved_weekly,
        reinvestment_category=body.reinvestment_category,
        notes=body.notes,
    )
    summary = get_user_summary(db, user.id)
    return JSONResponse({
        "status": "ok",
        "tool_slug": entry.tool_slug,
        "summary": {
            "total_hours_weekly": summary["total_hours_weekly"],
            "total_hours_monthly": summary["total_hours_monthly"],
            "total_hours_yearly": summary["total_hours_yearly"],
            "tool_count": summary["tool_count"],
            "by_category": summary["by_category"],
        },
    })


@router.post("/api/remove", response_class=JSONResponse)
async def time_dividend_remove(
    body: RemoveEntryRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    _: None = Depends(require_time_dividend()),
):
    """Remove a time dividend entry."""
    removed = remove_entry(db, user.id, body.tool_slug)
    summary = get_user_summary(db, user.id)
    return JSONResponse({
        "status": "ok" if removed else "not_found",
        "summary": {
            "total_hours_weekly": summary["total_hours_weekly"],
            "total_hours_monthly": summary["total_hours_monthly"],
            "total_hours_yearly": summary["total_hours_yearly"],
            "tool_count": summary["tool_count"],
            "by_category": summary["by_category"],
        },
    })
