"""Governance admin routes for managing frameworks, tool tests, and content."""
import json
import time as time_module
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
import asyncio

from fastapi import APIRouter, Request, Depends, HTTPException, Form, Query, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, or_

from app.db import get_db
from app.dependencies import require_admin
from app.models.auth import User
from app.models.governance import (
    GovernanceTarget,
    GovernanceFramework,
    GovernanceControl,
    ToolsCatalogEntry,
    ToolTestCase,
    ToolTest,
    ContentItem,
)
from app.models.workflow import WorkflowRun
from app.templates_engine import templates
from app.products.admin_context import get_admin_context_dict
from app.workflows.audit import (
    log_workflow_start,
    log_workflow_complete,
    log_workflow_failure,
    log_content_action,
    log_rate_limit_hit,
    WorkflowAuditAction,
)
from app.workflows.rate_limit import check_workflow_rate_limit

router = APIRouter(prefix="/admin/governance", tags=["governance"])


# =============================================================================
# DASHBOARD
# =============================================================================

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def governance_dashboard(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Governance dashboard with overview stats."""
    # Get counts
    target_count = db.query(func.count(GovernanceTarget.id)).scalar() or 0
    queued_targets = db.query(func.count(GovernanceTarget.id)).filter(
        GovernanceTarget.status == "queued"
    ).scalar() or 0

    framework_count = db.query(func.count(GovernanceFramework.id)).scalar() or 0
    tool_count = db.query(func.count(ToolsCatalogEntry.id)).scalar() or 0

    content_pending = db.query(func.count(ContentItem.id)).filter(
        ContentItem.status == "pending_review"
    ).scalar() or 0
    content_published = db.query(func.count(ContentItem.id)).filter(
        ContentItem.status == "published"
    ).scalar() or 0

    # Recent activity
    recent_targets = (
        db.query(GovernanceTarget)
        .order_by(desc(GovernanceTarget.created_at))
        .limit(5)
        .all()
    )

    recent_tests = (
        db.query(ToolTest)
        .options(joinedload(ToolTest.tool))
        .order_by(desc(ToolTest.created_at))
        .limit(5)
        .all()
    )

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/governance/dashboard.html",
        {
            "request": request,
            "user": user,
            "stats": {
                "targets": target_count,
                "queued_targets": queued_targets,
                "frameworks": framework_count,
                "tools": tool_count,
                "content_pending": content_pending,
                "content_published": content_published,
            },
            "recent_targets": recent_targets,
            "recent_tests": recent_tests,
            **admin_context,
            "active_admin_page": "governance",
        }
    )


# =============================================================================
# GOVERNANCE TARGETS
# =============================================================================

@router.get("/targets", response_class=HTMLResponse)
async def list_targets(
    request: Request,
    status: Optional[str] = Query(None),
    target_type: Optional[str] = Query(None),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List governance targets queue."""
    query = db.query(GovernanceTarget)

    if status:
        query = query.filter(GovernanceTarget.status == status)
    if target_type:
        query = query.filter(GovernanceTarget.target_type == target_type)

    targets = query.order_by(
        GovernanceTarget.priority,
        GovernanceTarget.queued_at
    ).all()

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/governance/targets.html",
        {
            "request": request,
            "user": user,
            "targets": targets,
            "filters": {"status": status, "target_type": target_type},
            **admin_context,
            "active_admin_page": "governance",
        }
    )


@router.get("/targets/new", response_class=HTMLResponse)
async def new_target_form(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Show form to create a new governance target."""
    tools = db.query(ToolsCatalogEntry).order_by(ToolsCatalogEntry.name).all()

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/governance/target_form.html",
        {
            "request": request,
            "user": user,
            "target": None,
            "tools": tools,
            **admin_context,
            "active_admin_page": "governance",
        }
    )


@router.post("/targets")
async def create_target(
    request: Request,
    target_type: str = Form(...),
    target_name: str = Form(...),
    target_description: str = Form(None),
    jurisdiction: str = Form(None),
    tool_id: str = Form(None),
    search_terms: str = Form(None),
    known_urls: str = Form(None),
    priority: int = Form(5),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a new governance target."""
    target = GovernanceTarget(
        target_type=target_type,
        target_name=target_name,
        target_description=target_description or None,
        jurisdiction=jurisdiction or None,
        tool_id=UUID(tool_id) if tool_id else None,
        search_terms=[s.strip() for s in search_terms.split(",") if s.strip()] if search_terms else [],
        known_urls=[u.strip() for u in known_urls.split("\n") if u.strip()] if known_urls else [],
        priority=priority,
        queued_by=user.id,
    )
    db.add(target)
    db.commit()

    return RedirectResponse(url="/admin/governance/targets", status_code=303)


@router.post("/targets/{target_id}/run")
async def run_target(
    target_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Run the governance workflow for a target."""
    target = db.query(GovernanceTarget).filter(GovernanceTarget.id == UUID(target_id)).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    if target.status == "processing":
        raise HTTPException(status_code=400, detail="Target is already processing")

    # Check rate limit
    allowed, retry_after, reason = check_workflow_rate_limit(
        workflow_name="governance_intelligence",
        user_id=str(user.id),
        resource_id=target_id,
    )
    if not allowed:
        log_rate_limit_hit(
            workflow_name="governance_intelligence",
            actor_id=str(user.id),
            actor_email=user.email,
            resource_type="governance_target",
            resource_id=target_id,
        )
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )

    # Create workflow run
    workflow_run = WorkflowRun(
        workflow_name="governance_intelligence",
        workflow_version="1.0.0",
        status="queued",
        inputs={
            "target_id": str(target.id),
            "target_type": target.target_type,
            "target_name": target.target_name,
            "target_description": target.target_description or "",
            "jurisdiction": target.jurisdiction or "",
            "tool_id": str(target.tool_id) if target.tool_id else "",
            "search_terms": target.search_terms or [],
            "known_urls": target.known_urls or [],
        },
        triggered_by=user.id,
    )
    db.add(workflow_run)

    # Update target status
    target.status = "processing"
    target.started_at = datetime.now(timezone.utc)
    target.workflow_run_id = workflow_run.id

    db.commit()

    # Log workflow start
    log_workflow_start(
        workflow_name="governance_intelligence",
        workflow_run_id=str(workflow_run.id),
        actor_id=str(user.id),
        actor_email=user.email,
        resource_type="governance_target",
        resource_id=target_id,
        inputs_summary={"target_name": target.target_name, "target_type": target.target_type},
    )

    # Run workflow in background
    async def run_workflow_task():
        from app.db import SessionLocal
        from app.workflows.governance import run_governance_workflow

        start_time = time_module.time()
        db_task = SessionLocal()
        try:
            # Update run status
            run = db_task.query(WorkflowRun).filter(WorkflowRun.id == workflow_run.id).first()
            run.status = "running"
            run.started_at = datetime.now(timezone.utc)
            db_task.commit()

            # Run the workflow
            result = await run_governance_workflow(
                target_id=str(target.id),
                target_type=target.target_type,
                target_name=target.target_name,
                target_description=target.target_description or "",
                jurisdiction=target.jurisdiction or "",
                tool_id=str(target.tool_id) if target.tool_id else "",
                tool_url=target.tool.url if target.tool else "",
                search_terms=target.search_terms or [],
                known_urls=target.known_urls or [],
                workflow_run_id=str(workflow_run.id),
            )

            # Update run with results
            run.status = "needs_review" if result.get("needs_review") else "completed"
            run.completed_at = datetime.now(timezone.utc)
            run.outputs = {
                "framework_id": result.get("framework_id"),
                "content_item_ids": result.get("content_item_ids", []),
                "test_results": result.get("test_results", []),
                "errors": result.get("errors", []),
            }
            run.review_required = result.get("review_reason")

            # Update target
            tgt = db_task.query(GovernanceTarget).filter(GovernanceTarget.id == target.id).first()
            tgt.status = "completed" if not result.get("errors") else "failed"
            tgt.completed_at = datetime.now(timezone.utc)
            tgt.output_content_ids = result.get("content_item_ids", [])
            tgt.output_framework_id = UUID(result["framework_id"]) if result.get("framework_id") else None
            tgt.processing_notes = result.get("processing_notes", "")
            if result.get("errors"):
                tgt.error_message = "\n".join(result["errors"])

            db_task.commit()

            # Log workflow completion
            log_workflow_complete(
                workflow_name="governance_intelligence",
                workflow_run_id=str(workflow_run.id),
                actor_id=str(user.id),
                outputs_summary={"content_items": len(result.get("content_item_ids", []))},
                duration_seconds=time_module.time() - start_time,
            )

        except Exception as e:
            # Log workflow failure
            log_workflow_failure(
                workflow_name="governance_intelligence",
                workflow_run_id=str(workflow_run.id),
                error_message=str(e),
                actor_id=str(user.id),
            )

            run = db_task.query(WorkflowRun).filter(WorkflowRun.id == workflow_run.id).first()
            run.status = "failed"
            run.completed_at = datetime.now(timezone.utc)
            run.error_message = str(e)

            tgt = db_task.query(GovernanceTarget).filter(GovernanceTarget.id == target.id).first()
            tgt.status = "failed"
            tgt.error_message = str(e)

            db_task.commit()

        finally:
            db_task.close()

    background_tasks.add_task(asyncio.create_task, run_workflow_task())

    return {"status": "started", "workflow_run_id": str(workflow_run.id)}


@router.post("/targets/{target_id}/cancel")
async def cancel_target(
    target_id: str,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Cancel a queued or processing target."""
    target = db.query(GovernanceTarget).filter(GovernanceTarget.id == UUID(target_id)).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    if target.status not in ["queued", "processing"]:
        raise HTTPException(status_code=400, detail="Target cannot be cancelled")

    target.status = "cancelled"
    db.commit()

    return {"status": "cancelled"}


@router.delete("/targets/{target_id}")
async def delete_target(
    target_id: str,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete a governance target."""
    target = db.query(GovernanceTarget).filter(GovernanceTarget.id == UUID(target_id)).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    db.delete(target)
    db.commit()

    return {"status": "deleted"}


# =============================================================================
# FRAMEWORK LIBRARY
# =============================================================================

@router.get("/frameworks", response_class=HTMLResponse)
async def list_frameworks(
    request: Request,
    jurisdiction: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List governance frameworks."""
    query = db.query(GovernanceFramework)

    if jurisdiction:
        query = query.filter(GovernanceFramework.jurisdiction == jurisdiction)
    if status:
        query = query.filter(GovernanceFramework.status == status)
    if search:
        query = query.filter(
            or_(
                GovernanceFramework.name.ilike(f"%{search}%"),
                GovernanceFramework.short_name.ilike(f"%{search}%"),
            )
        )

    frameworks = query.order_by(GovernanceFramework.name).all()

    # Get unique jurisdictions for filter
    jurisdictions = db.query(GovernanceFramework.jurisdiction).distinct().all()

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/governance/frameworks.html",
        {
            "request": request,
            "user": user,
            "frameworks": frameworks,
            "jurisdictions": [j[0] for j in jurisdictions if j[0]],
            "filters": {"jurisdiction": jurisdiction, "status": status, "search": search},
            **admin_context,
            "active_admin_page": "governance",
        }
    )


@router.get("/frameworks/{framework_id}", response_class=HTMLResponse)
async def view_framework(
    framework_id: str,
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """View framework details."""
    framework = (
        db.query(GovernanceFramework)
        .options(joinedload(GovernanceFramework.controls))
        .filter(GovernanceFramework.id == UUID(framework_id))
        .first()
    )
    if not framework:
        raise HTTPException(status_code=404, detail="Framework not found")

    # Get related content
    content_items = (
        db.query(ContentItem)
        .filter(ContentItem.framework_id == framework.id)
        .order_by(desc(ContentItem.created_at))
        .all()
    )

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/governance/framework_detail.html",
        {
            "request": request,
            "user": user,
            "framework": framework,
            "content_items": content_items,
            **admin_context,
            "active_admin_page": "governance",
        }
    )


@router.post("/frameworks/{framework_id}/status")
async def update_framework_status(
    framework_id: str,
    status: str = Form(...),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update framework status."""
    framework = db.query(GovernanceFramework).filter(GovernanceFramework.id == UUID(framework_id)).first()
    if not framework:
        raise HTTPException(status_code=404, detail="Framework not found")

    if status not in ["draft", "active", "superseded", "archived"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    framework.status = status
    db.commit()

    return {"status": "updated", "framework_status": status}


# =============================================================================
# TOOL TESTS
# =============================================================================

@router.get("/tools", response_class=HTMLResponse)
async def list_tools(
    request: Request,
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List tools in catalog with test status."""
    query = db.query(ToolsCatalogEntry)

    if search:
        query = query.filter(ToolsCatalogEntry.name.ilike(f"%{search}%"))
    if status == "passed":
        query = query.filter(ToolsCatalogEntry.last_test_passed == True)
    elif status == "failed":
        query = query.filter(ToolsCatalogEntry.last_test_passed == False)
    elif status == "untested":
        query = query.filter(ToolsCatalogEntry.last_tested_at.is_(None))

    tools = query.order_by(ToolsCatalogEntry.name).all()

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/governance/tools.html",
        {
            "request": request,
            "user": user,
            "tools": tools,
            "filters": {"status": status, "search": search},
            **admin_context,
            "active_admin_page": "governance_tools",
        }
    )


@router.get("/tools/new", response_class=HTMLResponse)
async def new_tool_form(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Show form to add a tool to catalog."""
    # Get discovered tools that aren't in catalog yet
    from app.models.discovery import DiscoveredTool

    discovered_tools = (
        db.query(DiscoveredTool)
        .outerjoin(ToolsCatalogEntry, ToolsCatalogEntry.discovered_tool_id == DiscoveredTool.id)
        .filter(
            DiscoveredTool.status == "approved",
            ToolsCatalogEntry.id.is_(None)
        )
        .order_by(DiscoveredTool.name)
        .all()
    )

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/governance/tool_form.html",
        {
            "request": request,
            "user": user,
            "tool": None,
            "discovered_tools": discovered_tools,
            **admin_context,
            "active_admin_page": "governance_tools",
        }
    )


@router.post("/tools")
async def create_tool(
    request: Request,
    name: str = Form(...),
    url: str = Form(None),
    description: str = Form(None),
    discovered_tool_id: str = Form(None),
    is_testable: bool = Form(True),
    test_frequency: str = Form("weekly"),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Add a tool to the catalog."""
    import re

    # Generate slug
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = slug.strip('-')[:100]

    # Check for existing slug
    existing = db.query(ToolsCatalogEntry).filter(ToolsCatalogEntry.slug == slug).first()
    if existing:
        slug = f"{slug}-{datetime.now().strftime('%Y%m%d')}"

    tool = ToolsCatalogEntry(
        name=name,
        slug=slug,
        url=url or None,
        description=description or None,
        discovered_tool_id=UUID(discovered_tool_id) if discovered_tool_id else None,
        is_testable=is_testable,
        test_frequency=test_frequency,
    )
    db.add(tool)
    db.commit()

    return RedirectResponse(url="/admin/governance/tools", status_code=303)


@router.get("/tools/{tool_id}", response_class=HTMLResponse)
async def view_tool(
    tool_id: str,
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """View tool details and test history."""
    tool = (
        db.query(ToolsCatalogEntry)
        .filter(ToolsCatalogEntry.id == UUID(tool_id))
        .first()
    )
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    # Get test history
    tests = (
        db.query(ToolTest)
        .filter(ToolTest.tool_id == tool.id)
        .order_by(desc(ToolTest.created_at))
        .limit(20)
        .all()
    )

    # Get test cases
    test_cases = (
        db.query(ToolTestCase)
        .filter(
            or_(ToolTestCase.tool_id == tool.id, ToolTestCase.tool_id.is_(None))
        )
        .filter(ToolTestCase.is_active == True)
        .all()
    )

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/governance/tool_detail.html",
        {
            "request": request,
            "user": user,
            "tool": tool,
            "tests": tests,
            "test_cases": test_cases,
            **admin_context,
            "active_admin_page": "governance_tools",
        }
    )


@router.post("/tools/{tool_id}/test")
async def run_tool_test(
    tool_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Run tests for a tool."""
    tool = db.query(ToolsCatalogEntry).filter(ToolsCatalogEntry.id == UUID(tool_id)).first()
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    if not tool.url:
        raise HTTPException(status_code=400, detail="Tool has no URL configured")

    # Create a governance target for this tool
    target = GovernanceTarget(
        target_type="tool",
        target_name=tool.name,
        tool_id=tool.id,
        priority=1,  # High priority for manual tests
        queued_by=user.id,
    )
    db.add(target)
    db.commit()

    # Trigger the workflow
    return await run_target(str(target.id), background_tasks, user, db)


# =============================================================================
# CONTENT REVIEW
# =============================================================================

@router.get("/content", response_class=HTMLResponse)
async def list_content(
    request: Request,
    status: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List content items."""
    query = db.query(ContentItem)

    if status:
        query = query.filter(ContentItem.status == status)
    if section:
        query = query.filter(ContentItem.section == section)
    if search:
        query = query.filter(
            or_(
                ContentItem.title.ilike(f"%{search}%"),
                ContentItem.slug.ilike(f"%{search}%"),
            )
        )

    content_items = query.order_by(desc(ContentItem.created_at)).all()

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/governance/content.html",
        {
            "request": request,
            "user": user,
            "content_items": content_items,
            "filters": {"status": status, "section": section, "search": search},
            **admin_context,
            "active_admin_page": "governance_content",
        }
    )


@router.get("/content/review", response_class=HTMLResponse)
async def content_review_queue(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Show content pending review."""
    pending_items = (
        db.query(ContentItem)
        .filter(ContentItem.status == "pending_review")
        .order_by(ContentItem.created_at)
        .all()
    )

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/governance/content_review.html",
        {
            "request": request,
            "user": user,
            "pending_items": pending_items,
            **admin_context,
            "active_admin_page": "governance_content",
        }
    )


@router.get("/content/{content_id}", response_class=HTMLResponse)
async def view_content(
    content_id: str,
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """View content item details."""
    item = db.query(ContentItem).filter(ContentItem.id == UUID(content_id)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/governance/content_detail.html",
        {
            "request": request,
            "user": user,
            "item": item,
            **admin_context,
            "active_admin_page": "governance_content",
        }
    )


@router.post("/content/{content_id}/approve")
async def approve_content(
    content_id: str,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Approve content for publishing."""
    item = db.query(ContentItem).filter(ContentItem.id == UUID(content_id)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")

    item.status = "approved"
    item.reviewed_by = user.id
    item.reviewed_at = datetime.now(timezone.utc)
    db.commit()

    # Log audit event
    log_content_action(
        action=WorkflowAuditAction.CONTENT_APPROVED,
        content_id=content_id,
        content_title=item.title,
        actor_id=str(user.id),
        actor_email=user.email,
    )

    return {"status": "approved"}


@router.post("/content/{content_id}/publish")
async def publish_content(
    content_id: str,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Publish content."""
    item = db.query(ContentItem).filter(ContentItem.id == UUID(content_id)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")

    if item.status not in ["approved", "pending_review"]:
        raise HTTPException(status_code=400, detail="Content must be approved first")

    item.status = "published"
    item.published_by = user.id
    item.published_at = datetime.now(timezone.utc)
    if not item.reviewed_by:
        item.reviewed_by = user.id
        item.reviewed_at = datetime.now(timezone.utc)
    db.commit()

    # Log audit event
    log_content_action(
        action=WorkflowAuditAction.CONTENT_PUBLISHED,
        content_id=content_id,
        content_title=item.title,
        actor_id=str(user.id),
        actor_email=user.email,
    )

    return {"status": "published"}


@router.post("/content/{content_id}/unpublish")
async def unpublish_content(
    content_id: str,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Unpublish content (back to approved)."""
    item = db.query(ContentItem).filter(ContentItem.id == UUID(content_id)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")

    item.status = "approved"
    db.commit()

    # Log audit event
    log_content_action(
        action=WorkflowAuditAction.CONTENT_UNPUBLISHED,
        content_id=content_id,
        content_title=item.title,
        actor_id=str(user.id),
        actor_email=user.email,
    )

    return {"status": "unpublished"}


@router.post("/content/{content_id}/reject")
async def reject_content(
    content_id: str,
    reason: str = Form(None),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Reject content."""
    item = db.query(ContentItem).filter(ContentItem.id == UUID(content_id)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")

    item.status = "archived"
    item.reviewed_by = user.id
    item.reviewed_at = datetime.now(timezone.utc)
    item.review_notes = reason
    db.commit()

    return {"status": "rejected"}


@router.post("/content/{content_id}/edit")
async def edit_content(
    content_id: str,
    title: str = Form(...),
    content_markdown: str = Form(...),
    summary: str = Form(None),
    tags: str = Form(None),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Edit content item."""
    item = db.query(ContentItem).filter(ContentItem.id == UUID(content_id)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")

    item.title = title
    item.content_markdown = content_markdown
    item.summary = summary
    if tags:
        item.tags = [t.strip() for t in tags.split(",") if t.strip()]

    db.commit()

    return RedirectResponse(url=f"/admin/governance/content/{content_id}", status_code=303)


# =============================================================================
# ETHICS POLICY ADMIN
# =============================================================================

@router.get("/ethics-policy", response_class=HTMLResponse)
async def admin_ethics_policy(
    request: Request,
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin view for Ethics Policy content items."""
    query = db.query(ContentItem).filter(ContentItem.section == "ethics_policy")

    if status:
        query = query.filter(ContentItem.status == status)
    if search:
        query = query.filter(
            or_(
                ContentItem.title.ilike(f"%{search}%"),
                ContentItem.slug.ilike(f"%{search}%"),
            )
        )

    content_items = query.order_by(desc(ContentItem.created_at)).all()

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/governance/content.html",
        {
            "request": request,
            "user": user,
            "content_items": content_items,
            "filters": {"status": status, "section": "ethics_policy", "search": search},
            "section_title": "AI Ethics Policy",
            **admin_context,
            "active_admin_page": "ethics_policy",
        }
    )


# =============================================================================
# LEGAL FRAMEWORK ADMIN
# =============================================================================

@router.get("/legal-framework", response_class=HTMLResponse)
async def admin_legal_framework(
    request: Request,
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin view for Legal Framework content items."""
    query = db.query(ContentItem).filter(ContentItem.section == "legal_framework")

    if status:
        query = query.filter(ContentItem.status == status)
    if search:
        query = query.filter(
            or_(
                ContentItem.title.ilike(f"%{search}%"),
                ContentItem.slug.ilike(f"%{search}%"),
            )
        )

    content_items = query.order_by(desc(ContentItem.created_at)).all()

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/governance/content.html",
        {
            "request": request,
            "user": user,
            "content_items": content_items,
            "filters": {"status": status, "section": "legal_framework", "search": search},
            "section_title": "AI Legal Framework",
            **admin_context,
            "active_admin_page": "legal_framework",
        }
    )


# =============================================================================
# WORKFLOW RUNS
# =============================================================================

@router.get("/runs", response_class=HTMLResponse)
async def list_workflow_runs(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List governance workflow runs."""
    runs = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.workflow_name == "governance_intelligence")
        .order_by(desc(WorkflowRun.created_at))
        .limit(50)
        .all()
    )

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/governance/runs.html",
        {
            "request": request,
            "user": user,
            "runs": runs,
            **admin_context,
            "active_admin_page": "governance",
        }
    )
