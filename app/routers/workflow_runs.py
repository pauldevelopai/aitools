"""Unified workflow runs admin routes for viewing all workflow executions."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, or_

from app.db import get_db
from app.dependencies import require_admin
from app.models.auth import User
from app.models.workflow import WorkflowRun
from app.templates_engine import templates
from app.products.admin_context import get_admin_context_dict

router = APIRouter(prefix="/admin/workflows", tags=["workflows"])


@router.get("/runs", response_class=HTMLResponse)
async def unified_workflow_runs(
    request: Request,
    workflow: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=10, le=100),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Unified view of all workflow runs across all workflow types."""
    query = db.query(WorkflowRun)

    # Filter by workflow type
    if workflow:
        query = query.filter(WorkflowRun.workflow_name == workflow)

    # Filter by status
    if status:
        query = query.filter(WorkflowRun.status == status)

    # Search in inputs (target name, organization name, etc.)
    if search:
        query = query.filter(
            or_(
                WorkflowRun.inputs["target_name"].astext.ilike(f"%{search}%"),
                WorkflowRun.inputs["organization_name"].astext.ilike(f"%{search}%"),
                WorkflowRun.inputs["journalist_name"].astext.ilike(f"%{search}%"),
            )
        )

    # Get total count
    total_count = query.count()

    # Paginate and order
    runs = (
        query
        .order_by(desc(WorkflowRun.created_at))
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    # Get unique workflow names for filter dropdown
    workflow_names = (
        db.query(WorkflowRun.workflow_name)
        .distinct()
        .order_by(WorkflowRun.workflow_name)
        .all()
    )

    # Get stats
    stats = {
        "total": db.query(func.count(WorkflowRun.id)).scalar() or 0,
        "running": db.query(func.count(WorkflowRun.id)).filter(WorkflowRun.status == "running").scalar() or 0,
        "completed": db.query(func.count(WorkflowRun.id)).filter(WorkflowRun.status == "completed").scalar() or 0,
        "failed": db.query(func.count(WorkflowRun.id)).filter(WorkflowRun.status == "failed").scalar() or 0,
        "needs_review": db.query(func.count(WorkflowRun.id)).filter(WorkflowRun.status == "needs_review").scalar() or 0,
    }

    # Calculate pagination
    total_pages = (total_count + per_page - 1) // per_page

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/workflow_runs.html",
        {
            "request": request,
            "user": user,
            "runs": runs,
            "stats": stats,
            "workflow_names": [w[0] for w in workflow_names],
            "filters": {
                "workflow": workflow,
                "status": status,
                "search": search,
            },
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_count": total_count,
                "total_pages": total_pages,
            },
            **admin_context,
            "active_admin_page": "workflows",
        }
    )


@router.get("/runs/{run_id}", response_class=HTMLResponse)
async def workflow_run_detail(
    run_id: str,
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """View detailed information about a specific workflow run."""
    run = (
        db.query(WorkflowRun)
        .options(joinedload(WorkflowRun.triggerer))
        .filter(WorkflowRun.id == UUID(run_id))
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    # Get linked entity information based on workflow type
    linked_entity = None
    linked_entity_type = None
    linked_entity_url = None

    if run.inputs:
        if run.workflow_name == "partner_intelligence":
            from app.models.directory import MediaOrganization
            org_id = run.inputs.get("organization_id")
            if org_id:
                org = db.query(MediaOrganization).filter(MediaOrganization.id == org_id).first()
                if org:
                    linked_entity = org
                    linked_entity_type = "organization"
                    linked_entity_url = f"/admin/directory/organizations/{org.id}"

        elif run.workflow_name in ["mentor_intake", "mentor_pre_call", "mentor_post_call"]:
            from app.models.directory import Engagement
            eng_id = run.inputs.get("engagement_id")
            if eng_id:
                eng = db.query(Engagement).filter(Engagement.id == eng_id).first()
                if eng:
                    linked_entity = eng
                    linked_entity_type = "engagement"
                    linked_entity_url = f"/admin/directory/engagements/{eng.id}/mentor"

        elif run.workflow_name == "governance_intelligence":
            from app.models.governance import GovernanceTarget
            target_id = run.inputs.get("target_id")
            if target_id:
                target = db.query(GovernanceTarget).filter(GovernanceTarget.id == target_id).first()
                if target:
                    linked_entity = target
                    linked_entity_type = "governance_target"
                    linked_entity_url = f"/admin/governance/targets"

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/workflow_run_detail.html",
        {
            "request": request,
            "user": user,
            "run": run,
            "linked_entity": linked_entity,
            "linked_entity_type": linked_entity_type,
            "linked_entity_url": linked_entity_url,
            **admin_context,
            "active_admin_page": "workflows",
        }
    )


@router.get("/api/runs/{run_id}")
async def get_workflow_run_api(
    run_id: str,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """API endpoint to get workflow run details."""
    run = db.query(WorkflowRun).filter(WorkflowRun.id == UUID(run_id)).first()
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    return {
        "id": str(run.id),
        "workflow_name": run.workflow_name,
        "status": run.status,
        "queued_at": run.queued_at.isoformat() if run.queued_at else None,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "inputs": run.inputs,
        "outputs": run.outputs,
        "error_message": run.error_message,
        "review_required": run.review_required,
    }
