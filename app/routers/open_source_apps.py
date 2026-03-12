"""Open Source Apps public directory routes."""
from typing import Optional

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models.auth import User
from app.products.guards import require_open_source_apps
from app.templates_engine import templates
from app.services import open_source_apps as apps_service
from app.services.lessons import get_lessons_for_app

router = APIRouter(prefix="/apps", tags=["open_source_apps"])


@router.get("/", response_class=HTMLResponse)
async def app_directory(
    request: Request,
    deployment_type: Optional[str] = None,
    difficulty: Optional[str] = None,
    platform: Optional[str] = None,
    user: Optional[User] = Depends(get_current_user),
    _feature: None = Depends(require_open_source_apps()),
    db: Session = Depends(get_db),
):
    """Public app directory listing."""
    apps = apps_service.get_apps(
        db,
        deployment_type=deployment_type,
        difficulty=difficulty,
        platform=platform,
    )
    stats = apps_service.get_directory_stats(db)

    return templates.TemplateResponse(
        "open_source_apps/directory.html",
        {
            "request": request,
            "user": user,
            "apps": apps,
            "stats": stats,
            "active_deployment_type": deployment_type,
            "active_difficulty": difficulty,
            "active_platform": platform,
            "requires_login": not user,
        },
    )


@router.get("/{slug}", response_class=HTMLResponse)
async def app_detail(
    slug: str,
    request: Request,
    user: Optional[User] = Depends(get_current_user),
    _feature: None = Depends(require_open_source_apps()),
    db: Session = Depends(get_db),
):
    """Single app detail page with installation guide."""
    app = apps_service.get_app_by_slug(db, slug)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")

    # Only show published apps publicly
    if app.status != "published":
        raise HTTPException(status_code=404, detail="App not found")

    # Find lessons that reference this app
    related_lessons = get_lessons_for_app(db, slug)

    return templates.TemplateResponse(
        "open_source_apps/detail.html",
        {
            "request": request,
            "user": user,
            "app": app,
            "related_lessons": related_lessons,
            "requires_login": not user,
        },
    )
