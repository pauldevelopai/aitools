"""Workflow Templates service.

Manages reusable multi-step AI workflow templates
and tracks user workflow runs.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.models.workflow_template import WorkflowTemplate
from app.models.workflow import WorkflowRun

logger = logging.getLogger(__name__)


def get_templates(
    db: Session,
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Get published templates, optionally filtered."""
    query = db.query(WorkflowTemplate).filter(
        WorkflowTemplate.status == "published"
    )

    if category:
        query = query.filter(WorkflowTemplate.category == category)
    if difficulty:
        query = query.filter(WorkflowTemplate.difficulty == difficulty)

    templates = (
        query
        .order_by(WorkflowTemplate.usage_count.desc(), WorkflowTemplate.name)
        .all()
    )

    return [_template_to_dict(t) for t in templates]


def get_template_by_slug(db: Session, slug: str) -> Optional[WorkflowTemplate]:
    """Get a single template by slug."""
    return (
        db.query(WorkflowTemplate)
        .filter(WorkflowTemplate.slug == slug)
        .first()
    )


def get_featured_templates(db: Session, limit: int = 3) -> list[dict]:
    """Get featured templates for highlights."""
    templates = (
        db.query(WorkflowTemplate)
        .filter(
            WorkflowTemplate.status == "published",
            WorkflowTemplate.is_featured.is_(True),
        )
        .order_by(WorkflowTemplate.usage_count.desc())
        .limit(limit)
        .all()
    )
    return [_template_to_dict(t) for t in templates]


def start_workflow(
    db: Session,
    user_id,
    template_id,
    inputs: Optional[dict] = None,
) -> dict[str, Any]:
    """Start a new workflow run from a template."""
    template = db.query(WorkflowTemplate).filter(
        WorkflowTemplate.id == template_id
    ).first()

    if not template:
        return {"error": "Template not found"}

    # Create workflow run
    run = WorkflowRun(
        workflow_name=template.name,
        workflow_version="template-v1",
        status="running",
        triggered_by=user_id,
        inputs=inputs or {},
        state={"current_step": 1, "total_steps": len(template.steps or [])},
        tags=["template", template.slug],
    )

    # Set template_id if column exists
    if hasattr(WorkflowRun, "template_id"):
        run.template_id = template_id

    run.started_at = datetime.now(timezone.utc)
    db.add(run)

    # Increment usage count
    template.usage_count = (template.usage_count or 0) + 1

    db.commit()
    db.refresh(run)

    return {
        "run_id": str(run.id),
        "template_slug": template.slug,
        "template_name": template.name,
        "status": run.status,
        "steps": template.steps or [],
        "current_step": 1,
    }


def get_user_workflow_runs(
    db: Session,
    user_id,
    template_id=None,
) -> list[dict]:
    """Get a user's workflow run history."""
    query = db.query(WorkflowRun).filter(
        WorkflowRun.triggered_by == user_id
    )

    if template_id and hasattr(WorkflowRun, "template_id"):
        query = query.filter(WorkflowRun.template_id == template_id)

    runs = (
        query
        .order_by(WorkflowRun.created_at.desc())
        .limit(50)
        .all()
    )

    return [
        {
            "id": str(r.id),
            "workflow_name": r.workflow_name,
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "state": r.state or {},
        }
        for r in runs
    ]


def get_catalog_stats(db: Session) -> dict[str, Any]:
    """Stats for the template catalog page."""
    total = (
        db.query(sa_func.count(WorkflowTemplate.id))
        .filter(WorkflowTemplate.status == "published")
        .scalar()
    ) or 0

    total_runs = (
        db.query(sa_func.sum(WorkflowTemplate.usage_count))
        .filter(WorkflowTemplate.status == "published")
        .scalar()
    ) or 0

    categories = (
        db.query(
            WorkflowTemplate.category,
            sa_func.count(WorkflowTemplate.id),
        )
        .filter(WorkflowTemplate.status == "published")
        .group_by(WorkflowTemplate.category)
        .all()
    )

    return {
        "total_templates": total,
        "total_runs": int(total_runs),
        "categories": [{"category": c, "count": n} for c, n in categories],
    }


def _template_to_dict(t: WorkflowTemplate) -> dict[str, Any]:
    """Convert template model to dict."""
    return {
        "id": str(t.id),
        "slug": t.slug,
        "name": t.name,
        "description": t.description,
        "category": t.category,
        "steps": t.steps or [],
        "step_count": len(t.steps or []),
        "estimated_minutes": t.estimated_minutes,
        "difficulty": t.difficulty,
        "sectors": t.sectors or [],
        "tags": t.tags or [],
        "usage_count": t.usage_count or 0,
        "is_featured": t.is_featured,
    }
