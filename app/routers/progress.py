"""Progress tracker router."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_auth, require_auth_page
from app.models.auth import User
from app.products.guards import require_feature
from app.templates_engine import templates
from app.services.progress_tracker import refresh_progress, get_progress_summary

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("/", response_class=HTMLResponse)
async def progress_dashboard(
    request: Request,
    user: User = Depends(require_auth_page),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("progress_tracker")),
):
    """Full progress dashboard page."""
    progress = refresh_progress(db, user.id)
    summary = get_progress_summary(db, user.id)

    # Determine next recommended action
    next_action = None
    for item in summary["items"]:
        if not item["complete"]:
            next_action = item
            break

    return templates.TemplateResponse(
        "progress/dashboard.html",
        {
            "request": request,
            "user": user,
            "title": "My Progress",
            "progress": progress,
            "summary": summary,
            "next_action": next_action,
        },
    )


@router.get("/api/summary", response_class=JSONResponse)
async def progress_summary_api(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """JSON summary for sidebar widget."""
    summary = get_progress_summary(db, user.id)
    return summary
