"""Learning paths router."""
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user, require_auth
from app.models.auth import User
from app.products.guards import require_feature
from app.templates_engine import templates
from app.services.learning_paths import (
    get_paths_for_user,
    get_path_by_slug,
    get_enrollment,
    enroll_user,
    mark_step_complete,
)

router = APIRouter(prefix="/learning-paths", tags=["learning-paths"])


@router.get("/", response_class=HTMLResponse)
async def learning_paths_index(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("learning_paths")),
):
    """Browse all learning paths."""
    sector = user.organisation_type if user else None
    paths = get_paths_for_user(db, sector)

    # Attach enrollment data if logged in
    path_data = []
    for path in paths:
        enrollment = get_enrollment(db, user.id, path.id) if user else None
        path_data.append({
            "path": path,
            "enrollment": enrollment,
        })

    return templates.TemplateResponse(
        "learning_paths/index.html",
        {
            "request": request,
            "user": user,
            "title": "Learning Paths",
            "path_data": path_data,
        },
    )


@router.get("/{slug}", response_class=HTMLResponse)
async def learning_path_detail(
    request: Request,
    slug: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("learning_paths")),
):
    """View a specific learning path with progress."""
    path = get_path_by_slug(db, slug)
    if not path:
        raise HTTPException(status_code=404, detail="Learning path not found")

    enrollment = get_enrollment(db, user.id, path.id) if user else None
    completed_steps = set(enrollment.completed_steps) if enrollment else set()

    return templates.TemplateResponse(
        "learning_paths/detail.html",
        {
            "request": request,
            "user": user,
            "title": path.name,
            "path": path,
            "enrollment": enrollment,
            "completed_steps": completed_steps,
        },
    )


@router.post("/{slug}/enroll")
async def enroll_in_path(
    slug: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("learning_paths")),
):
    """Enroll in a learning path."""
    path = get_path_by_slug(db, slug)
    if not path:
        raise HTTPException(status_code=404, detail="Learning path not found")

    enroll_user(db, user.id, path.id)
    return RedirectResponse(url=f"/learning-paths/{slug}", status_code=303)


@router.post("/{slug}/steps/{step_id}/complete")
async def complete_step(
    slug: str,
    step_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("learning_paths")),
):
    """Mark a step as complete."""
    path = get_path_by_slug(db, slug)
    if not path:
        raise HTTPException(status_code=404, detail="Learning path not found")

    enrollment = mark_step_complete(db, user.id, path.id, step_id)
    if not enrollment:
        raise HTTPException(status_code=400, detail="Not enrolled in this path")

    return JSONResponse({"completion_pct": enrollment.completion_pct, "completed_steps": enrollment.completed_steps})
