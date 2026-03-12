"""Micro-lessons router — gamified learning with token rewards."""
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user, require_auth
from app.models.auth import User
from app.products.guards import require_feature
from app.templates_engine import templates
from app.services.lessons import (
    get_modules_for_user,
    get_module_by_slug,
    get_lesson_by_slugs,
    start_lesson,
    complete_lesson,
    get_user_lesson_progress,
    is_module_unlocked,
    _get_published_lessons,
    get_related_apps_for_lesson,
)
from app.services.gamification import get_profile

router = APIRouter(prefix="/lessons", tags=["lessons"])


class CompleteRequest(BaseModel):
    task_response: Optional[str] = None


@router.get("/", response_class=HTMLResponse)
async def lessons_index(
    request: Request,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("lessons")),
):
    """Modules overview — all modules with locked/unlocked status."""
    module_data = get_modules_for_user(db, user)
    token_profile = get_profile(db, user.id) if user else None

    return templates.TemplateResponse(
        "lessons/modules.html",
        {
            "request": request,
            "user": user,
            "title": "Lessons",
            "module_data": module_data,
            "token_profile": token_profile,
        },
    )


@router.get("/api/profile")
async def lessons_profile(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """JSON: token balance, streak, level."""
    profile = get_profile(db, user.id)
    return JSONResponse(profile)


@router.get("/{module_slug}", response_class=HTMLResponse)
async def module_detail(
    request: Request,
    module_slug: str,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("lessons")),
):
    """Module detail — ordered lesson cards with progress badges."""
    module = get_module_by_slug(db, module_slug)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    # Check unlock status
    if user:
        unlocked = is_module_unlocked(db, user.id, module, user=user) or module.order == 1
    else:
        unlocked = module.order == 1

    lessons = _get_published_lessons(db, module.id)
    progress_map = get_user_lesson_progress(db, user.id, module.id) if user else {}
    token_profile = get_profile(db, user.id) if user else None

    return templates.TemplateResponse(
        "lessons/module_detail.html",
        {
            "request": request,
            "user": user,
            "title": module.name,
            "module": module,
            "lessons": lessons,
            "progress_map": progress_map,
            "unlocked": unlocked,
            "token_profile": token_profile,
        },
    )


@router.get("/{module_slug}/{lesson_slug}", response_class=HTMLResponse)
async def lesson_detail(
    request: Request,
    module_slug: str,
    lesson_slug: str,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("lessons")),
):
    """Lesson page — content, task, feedback display."""
    lesson = get_lesson_by_slugs(db, module_slug, lesson_slug)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    module = get_module_by_slug(db, module_slug)

    # Fetch existing progress
    from app.models.lessons import UserLessonProgress as ULP
    progress = None
    if user:
        progress = (
            db.query(ULP)
            .filter(ULP.user_id == user.id, ULP.lesson_id == lesson.id)
            .first()
        )

    token_profile = get_profile(db, user.id) if user else None
    requires_login = user is None

    # Fetch related apps for cross-reference cards
    related_apps = get_related_apps_for_lesson(db, lesson)

    return templates.TemplateResponse(
        "lessons/lesson.html",
        {
            "request": request,
            "user": user,
            "title": lesson.title,
            "lesson": lesson,
            "module": module,
            "progress": progress,
            "token_profile": token_profile,
            "requires_login": requires_login,
            "related_apps": related_apps,
            "feature_name": "lessons",
            "feature_description": "Complete lessons to earn tokens and track your AI learning progress.",
        },
    )


@router.post("/{module_slug}/{lesson_slug}/start")
async def start_lesson_route(
    module_slug: str,
    lesson_slug: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("lessons")),
):
    """Begin lesson — creates progress record."""
    lesson = get_lesson_by_slugs(db, module_slug, lesson_slug)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    progress = start_lesson(db, user.id, lesson.id)
    return JSONResponse({"status": progress.status, "lesson_id": str(lesson.id)})


@router.post("/{module_slug}/{lesson_slug}/complete")
async def complete_lesson_route(
    module_slug: str,
    lesson_slug: str,
    body: CompleteRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("lessons")),
):
    """Submit task, run AI review if needed, earn tokens."""
    lesson = get_lesson_by_slugs(db, module_slug, lesson_slug)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    result = complete_lesson(db, user.id, lesson.id, body.task_response)
    return JSONResponse(result)
