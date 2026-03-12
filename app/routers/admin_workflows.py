"""Admin CRUD routes for Workflow Templates."""
import json
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_admin
from app.models.auth import User
from app.models.workflow_template import WorkflowTemplate
from app.templates_engine import templates
from app.products.admin_context import get_admin_context_dict

router = APIRouter(prefix="/admin/workflow-templates", tags=["admin-workflows"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_slug(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s-]+', '-', slug)
    return slug.strip('-')


def _parse_comma_list(raw: str | None) -> list | None:
    """Parse a comma-separated string into a cleaned list (or None)."""
    if not raw or not raw.strip():
        return None
    return [t.strip() for t in raw.split(",") if t.strip()]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_class=HTMLResponse)
async def list_workflow_templates(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all workflow templates."""
    admin_context = get_admin_context_dict(request)
    items = (
        db.query(WorkflowTemplate)
        .order_by(WorkflowTemplate.created_at.desc())
        .all()
    )

    return templates.TemplateResponse(
        "admin/workflows/list.html",
        {
            "request": request,
            "user": user,
            "items": items,
            **admin_context,
            "active_admin_page": "workflows_admin",
        },
    )


@router.get("/create", response_class=HTMLResponse)
async def create_workflow_template_form(
    request: Request,
    user: User = Depends(require_admin),
):
    """Show workflow template creation form."""
    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/workflows/form.html",
        {
            "request": request,
            "user": user,
            **admin_context,
            "active_admin_page": "workflows_admin",
        },
    )


@router.post("/create")
async def create_workflow_template(
    request: Request,
    name: str = Form(...),
    description: str = Form(None),
    category: str = Form(...),
    difficulty: str = Form("beginner"),
    estimated_minutes: int = Form(None),
    is_featured: bool = Form(False),
    sectors: str = Form(None),
    tags: str = Form(None),
    steps_json: str = Form("[]"),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a new workflow template."""
    slug = _generate_slug(name)
    existing = db.query(WorkflowTemplate).filter(WorkflowTemplate.slug == slug).first()
    if existing:
        slug = f"{slug}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    # Parse steps
    try:
        steps = json.loads(steps_json)
    except (json.JSONDecodeError, TypeError):
        steps = []

    template = WorkflowTemplate(
        name=name,
        slug=slug,
        description=description or None,
        category=category,
        difficulty=difficulty,
        estimated_minutes=estimated_minutes,
        is_featured=is_featured,
        sectors=_parse_comma_list(sectors),
        tags=_parse_comma_list(tags),
        steps=steps,
        created_by=admin_user.id,
    )
    db.add(template)
    db.commit()

    return RedirectResponse(
        url=f"/admin/workflow-templates/{template.id}", status_code=303
    )


@router.get("/{template_id}", response_class=HTMLResponse)
async def workflow_template_detail(
    template_id: str,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Workflow template detail / edit form."""
    tmpl = (
        db.query(WorkflowTemplate)
        .filter(WorkflowTemplate.id == template_id)
        .first()
    )
    if not tmpl:
        raise HTTPException(status_code=404, detail="Workflow template not found")

    # Convert JSONB lists to comma-separated strings for form inputs
    sectors_str = ", ".join(tmpl.sectors) if tmpl.sectors else ""
    tags_str = ", ".join(tmpl.tags) if tmpl.tags else ""
    steps_str = json.dumps(tmpl.steps or [], indent=2)

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/workflows/form.html",
        {
            "request": request,
            "user": admin_user,
            "template": tmpl,
            "sectors_str": sectors_str,
            "tags_str": tags_str,
            "steps_str": steps_str,
            **admin_context,
            "active_admin_page": "workflows_admin",
        },
    )


@router.post("/{template_id}/edit")
async def edit_workflow_template(
    template_id: str,
    name: str = Form(...),
    description: str = Form(None),
    category: str = Form(...),
    difficulty: str = Form("beginner"),
    estimated_minutes: int = Form(None),
    is_featured: bool = Form(False),
    sectors: str = Form(None),
    tags: str = Form(None),
    steps_json: str = Form("[]"),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update a workflow template."""
    tmpl = (
        db.query(WorkflowTemplate)
        .filter(WorkflowTemplate.id == template_id)
        .first()
    )
    if not tmpl:
        raise HTTPException(status_code=404, detail="Workflow template not found")

    tmpl.name = name
    tmpl.description = description or None
    tmpl.category = category
    tmpl.difficulty = difficulty
    tmpl.estimated_minutes = estimated_minutes
    tmpl.is_featured = is_featured
    tmpl.sectors = _parse_comma_list(sectors)
    tmpl.tags = _parse_comma_list(tags)

    # Parse steps
    try:
        tmpl.steps = json.loads(steps_json)
    except (json.JSONDecodeError, TypeError):
        pass  # keep existing steps on parse error

    db.commit()

    return RedirectResponse(
        url=f"/admin/workflow-templates/{template_id}", status_code=303
    )


@router.post("/{template_id}/toggle-publish")
async def toggle_workflow_template_publish(
    template_id: str,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Toggle status between draft and published."""
    tmpl = (
        db.query(WorkflowTemplate)
        .filter(WorkflowTemplate.id == template_id)
        .first()
    )
    if not tmpl:
        raise HTTPException(status_code=404, detail="Workflow template not found")

    tmpl.status = "draft" if tmpl.status == "published" else "published"
    db.commit()

    return RedirectResponse(url="/admin/workflow-templates", status_code=303)


@router.post("/{template_id}/toggle-featured")
async def toggle_workflow_template_featured(
    template_id: str,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Toggle is_featured flag."""
    tmpl = (
        db.query(WorkflowTemplate)
        .filter(WorkflowTemplate.id == template_id)
        .first()
    )
    if not tmpl:
        raise HTTPException(status_code=404, detail="Workflow template not found")

    tmpl.is_featured = not tmpl.is_featured
    db.commit()

    return RedirectResponse(url="/admin/workflow-templates", status_code=303)


@router.post("/{template_id}/delete")
async def delete_workflow_template(
    template_id: str,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete a workflow template."""
    tmpl = (
        db.query(WorkflowTemplate)
        .filter(WorkflowTemplate.id == template_id)
        .first()
    )
    if not tmpl:
        raise HTTPException(status_code=404, detail="Workflow template not found")

    db.delete(tmpl)
    db.commit()

    return RedirectResponse(url="/admin/workflow-templates", status_code=303)
