"""Workflow Templates router — reusable multi-step AI workflows."""
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.db import get_db
from app.dependencies import get_current_user, require_auth, require_auth_page
from app.models.auth import User
from app.products.guards import require_feature
from app.templates_engine import templates
from app.services.workflow_templates import (
    get_templates,
    get_template_by_slug,
    start_workflow,
    get_user_workflow_runs,
    get_catalog_stats,
)

router = APIRouter(prefix="/workflow-templates", tags=["workflow-templates"])


class StartWorkflowRequest(BaseModel):
    inputs: Optional[dict] = None


@router.get("/", response_class=HTMLResponse)
async def template_catalog(
    request: Request,
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("workflow_templates")),
):
    """Template catalog with category/difficulty filters."""
    template_list = get_templates(db, category=category, difficulty=difficulty)
    stats = get_catalog_stats(db)

    requires_login = user is None

    return templates.TemplateResponse(
        "workflow_templates/catalog.html",
        {
            "request": request,
            "user": user,
            "title": "Workflow Templates",
            "templates": template_list,
            "stats": stats,
            "active_category": category,
            "active_difficulty": difficulty,
            "requires_login": requires_login,
            "feature_name": "workflow templates",
            "feature_description": "Link modules into multi-step AI workflows that support real operational tasks.",
        },
    )


@router.get("/my-runs", response_class=HTMLResponse)
async def my_runs(
    request: Request,
    user: User = Depends(require_auth_page),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("workflow_templates")),
):
    """User's workflow run history."""
    runs = get_user_workflow_runs(db, user.id)

    return templates.TemplateResponse(
        "workflow_templates/runs.html",
        {
            "request": request,
            "user": user,
            "title": "My Workflow Runs",
            "runs": runs,
        },
    )


@router.get("/{slug}", response_class=HTMLResponse)
async def template_detail(
    request: Request,
    slug: str,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("workflow_templates")),
):
    """Template detail with steps breakdown."""
    template = get_template_by_slug(db, slug)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Get user's runs for this template
    runs = []
    if user and hasattr(template, "id"):
        runs = get_user_workflow_runs(db, user.id, template_id=template.id)

    requires_login = user is None

    return templates.TemplateResponse(
        "workflow_templates/detail.html",
        {
            "request": request,
            "user": user,
            "title": template.name,
            "template": template,
            "runs": runs,
            "requires_login": requires_login,
            "feature_name": "workflow templates",
            "feature_description": "Start structured workflows to accomplish real tasks with AI.",
        },
    )


@router.post("/{slug}/start")
async def start_workflow_route(
    slug: str,
    body: StartWorkflowRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("workflow_templates")),
):
    """Start a workflow run from a template."""
    template = get_template_by_slug(db, slug)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    result = start_workflow(db, user.id, template.id, body.inputs)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return JSONResponse(result)
