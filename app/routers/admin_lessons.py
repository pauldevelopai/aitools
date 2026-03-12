"""Admin routes for lesson module and lesson CRUD management."""
import re
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db import get_db
from app.dependencies import require_admin
from app.models.auth import User
from app.models.lessons import LessonModule, Lesson
from app.templates_engine import templates
from app.products.admin_context import get_admin_context_dict

router = APIRouter(prefix="/admin/lessons", tags=["admin-lessons"])


def _generate_slug(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s-]+', '-', slug)
    return slug.strip('-')


# ---------------------------------------------------------------------------
# Module routes
# ---------------------------------------------------------------------------

@router.get("", response_class=HTMLResponse)
async def list_modules(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all lesson modules with lesson count."""
    admin_context = get_admin_context_dict(request)

    lesson_count_sq = (
        db.query(Lesson.module_id, func.count(Lesson.id).label("lesson_count"))
        .group_by(Lesson.module_id)
        .subquery()
    )

    rows = (
        db.query(LessonModule, func.coalesce(lesson_count_sq.c.lesson_count, 0).label("lesson_count"))
        .outerjoin(lesson_count_sq, LessonModule.id == lesson_count_sq.c.module_id)
        .order_by(LessonModule.order, LessonModule.name)
        .all()
    )

    modules = [{"module": row[0], "lesson_count": row[1]} for row in rows]

    return templates.TemplateResponse(
        "admin/lessons/modules.html",
        {
            "request": request,
            "user": user,
            "modules": modules,
            **admin_context,
            "active_admin_page": "lessons_admin",
        },
    )


@router.get("/create-module", response_class=HTMLResponse)
async def create_module_form(
    request: Request,
    user: User = Depends(require_admin),
):
    """Show module creation form."""
    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/lessons/module_form.html",
        {
            "request": request,
            "user": user,
            **admin_context,
            "active_admin_page": "lessons_admin",
        },
    )


@router.post("/create-module")
async def create_module(
    name: str = Form(...),
    description: str = Form(None),
    sector: str = Form(None),
    difficulty: str = Form("beginner"),
    icon: str = Form(None),
    order: int = Form(1),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a new lesson module."""
    slug = _generate_slug(name)
    existing = db.query(LessonModule).filter(LessonModule.slug == slug).first()
    if existing:
        slug = f"{slug}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    module = LessonModule(
        name=name,
        slug=slug,
        description=description or None,
        sector=sector or None,
        difficulty=difficulty,
        icon=icon or None,
        order=order,
    )
    db.add(module)
    db.commit()

    return RedirectResponse(url=f"/admin/lessons/module/{module.id}", status_code=303)


@router.get("/module/{module_id}", response_class=HTMLResponse)
async def module_detail(
    module_id: str,
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Module detail page showing module info and lessons."""
    admin_context = get_admin_context_dict(request)

    module = db.query(LessonModule).filter(LessonModule.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    lessons = (
        db.query(Lesson)
        .filter(Lesson.module_id == module_id)
        .order_by(Lesson.order, Lesson.title)
        .all()
    )

    return templates.TemplateResponse(
        "admin/lessons/module_detail.html",
        {
            "request": request,
            "user": user,
            "module": module,
            "lessons": lessons,
            **admin_context,
            "active_admin_page": "lessons_admin",
        },
    )


@router.post("/module/{module_id}/edit")
async def edit_module(
    module_id: str,
    name: str = Form(...),
    description: str = Form(None),
    sector: str = Form(None),
    difficulty: str = Form("beginner"),
    icon: str = Form(None),
    order: int = Form(1),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update module fields."""
    module = db.query(LessonModule).filter(LessonModule.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    module.name = name
    module.description = description or None
    module.sector = sector or None
    module.difficulty = difficulty
    module.icon = icon or None
    module.order = order
    db.commit()

    return RedirectResponse(url=f"/admin/lessons/module/{module_id}", status_code=303)


@router.post("/module/{module_id}/toggle-active")
async def toggle_module_active(
    module_id: str,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Toggle module is_active."""
    module = db.query(LessonModule).filter(LessonModule.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    module.is_active = not module.is_active
    db.commit()

    return RedirectResponse(url=f"/admin/lessons/module/{module_id}", status_code=303)


@router.post("/module/{module_id}/delete")
async def delete_module(
    module_id: str,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete module (CASCADE deletes lessons)."""
    module = db.query(LessonModule).filter(LessonModule.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    db.delete(module)
    db.commit()

    return RedirectResponse(url="/admin/lessons", status_code=303)


# ---------------------------------------------------------------------------
# Lesson routes
# ---------------------------------------------------------------------------

@router.get("/module/{module_id}/create-lesson", response_class=HTMLResponse)
async def create_lesson_form(
    module_id: str,
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Show lesson creation form."""
    admin_context = get_admin_context_dict(request)

    module = db.query(LessonModule).filter(LessonModule.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    return templates.TemplateResponse(
        "admin/lessons/lesson_form.html",
        {
            "request": request,
            "user": user,
            "module": module,
            **admin_context,
            "active_admin_page": "lessons_admin",
        },
    )


@router.post("/module/{module_id}/create-lesson")
async def create_lesson(
    module_id: str,
    title: str = Form(...),
    description: str = Form(None),
    content_markdown: str = Form(...),
    learning_objectives: str = Form(None),
    task_type: str = Form("action"),
    task_prompt: str = Form(...),
    task_hints: str = Form(None),
    verification_type: str = Form("self_report"),
    token_reward: int = Form(1),
    estimated_minutes: int = Form(None),
    order: int = Form(1),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a new lesson."""
    module = db.query(LessonModule).filter(LessonModule.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    slug = _generate_slug(title)
    existing = db.query(Lesson).filter(Lesson.slug == slug).first()
    if existing:
        slug = f"{slug}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    # Parse comma-separated lists
    objectives_list = []
    if learning_objectives and learning_objectives.strip():
        objectives_list = [o.strip() for o in learning_objectives.split(",") if o.strip()]

    hints_list = None
    if task_hints and task_hints.strip():
        hints_list = [h.strip() for h in task_hints.split(",") if h.strip()]

    lesson = Lesson(
        module_id=module_id,
        title=title,
        slug=slug,
        description=description or None,
        content_markdown=content_markdown,
        learning_objectives=objectives_list,
        task_type=task_type,
        task_prompt=task_prompt,
        task_hints=hints_list,
        verification_type=verification_type,
        token_reward=token_reward,
        estimated_minutes=estimated_minutes,
        order=order,
        status="draft",
    )
    db.add(lesson)
    db.commit()

    return RedirectResponse(url=f"/admin/lessons/lesson/{lesson.id}", status_code=303)


@router.get("/lesson/{lesson_id}", response_class=HTMLResponse)
async def lesson_detail(
    lesson_id: str,
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Lesson edit form."""
    admin_context = get_admin_context_dict(request)

    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    module = db.query(LessonModule).filter(LessonModule.id == lesson.module_id).first()

    # Prepare comma-separated strings for form
    objectives_str = ", ".join(lesson.learning_objectives) if lesson.learning_objectives else ""
    hints_str = ", ".join(lesson.task_hints) if lesson.task_hints else ""

    return templates.TemplateResponse(
        "admin/lessons/lesson_form.html",
        {
            "request": request,
            "user": user,
            "lesson": lesson,
            "module": module,
            "objectives_str": objectives_str,
            "hints_str": hints_str,
            **admin_context,
            "active_admin_page": "lessons_admin",
        },
    )


@router.post("/lesson/{lesson_id}/edit")
async def edit_lesson(
    lesson_id: str,
    title: str = Form(...),
    description: str = Form(None),
    content_markdown: str = Form(...),
    learning_objectives: str = Form(None),
    task_type: str = Form("action"),
    task_prompt: str = Form(...),
    task_hints: str = Form(None),
    verification_type: str = Form("self_report"),
    token_reward: int = Form(1),
    estimated_minutes: int = Form(None),
    order: int = Form(1),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update a lesson."""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    lesson.title = title
    lesson.description = description or None
    lesson.content_markdown = content_markdown
    lesson.task_type = task_type
    lesson.task_prompt = task_prompt
    lesson.verification_type = verification_type
    lesson.token_reward = token_reward
    lesson.estimated_minutes = estimated_minutes
    lesson.order = order

    # Parse comma-separated lists
    if learning_objectives and learning_objectives.strip():
        lesson.learning_objectives = [o.strip() for o in learning_objectives.split(",") if o.strip()]
    else:
        lesson.learning_objectives = []

    if task_hints and task_hints.strip():
        lesson.task_hints = [h.strip() for h in task_hints.split(",") if h.strip()]
    else:
        lesson.task_hints = None

    db.commit()

    return RedirectResponse(url=f"/admin/lessons/lesson/{lesson_id}", status_code=303)


@router.post("/lesson/{lesson_id}/toggle-publish")
async def toggle_lesson_publish(
    lesson_id: str,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Toggle lesson status between draft and published."""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    lesson.status = "published" if lesson.status == "draft" else "draft"
    db.commit()

    return RedirectResponse(url=f"/admin/lessons/module/{lesson.module_id}", status_code=303)


@router.post("/lesson/{lesson_id}/delete")
async def delete_lesson(
    lesson_id: str,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete a lesson, redirect to module detail."""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    module_id = lesson.module_id
    db.delete(lesson)
    db.commit()

    return RedirectResponse(url=f"/admin/lessons/module/{module_id}", status_code=303)
