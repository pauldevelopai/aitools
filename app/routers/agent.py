"""AI Agent admin routes.

Provides a dashboard to launch, monitor, and review AI-powered
research missions that populate the database using the OpenAI Agents SDK.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_admin
from app.models.auth import User
from app.models.directory import MediaOrganization, Journalist, Engagement
from app.models.discovery import DiscoveredTool, DiscoveryRun
from app.models.usecase import UseCase
from app.models.governance import ContentItem
from app.models.workflow import WorkflowRun
from app.products.admin_context import get_admin_context_dict
from app.templates_engine import templates
from app.workflows.agent.engine import AgentEngine
from app.workflows.agent.missions import MISSIONS
from app.workflows.agent.quality_judge import judge_mission_results
from app.workflows.agent.scheduler import get_scheduler
from app.workflows.rate_limit import check_workflow_rate_limit
from app.workflows.runtime import WorkflowRuntime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/agent", tags=["agent"])


# ---------------------------------------------------------------------------
# Register the agent_mission workflow with WorkflowRuntime
# ---------------------------------------------------------------------------

async def _agent_mission_callable(inputs: dict, config: dict | None = None) -> dict:
    """Workflow callable registered with WorkflowRuntime.

    This is invoked by WorkflowRuntime.execute() but we handle execution
    ourselves via the background task pattern, so this is a no-op placeholder.
    """
    return inputs


WorkflowRuntime.register_workflow("agent_mission", _agent_mission_callable, version="1.0")


# ---------------------------------------------------------------------------
# Dashboard page
# ---------------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
async def agent_dashboard(
    request: Request,
    tab: str = Query("missions", alias="tab"),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """AI & Automation dashboard – Agent Missions, Discovery, GROUNDED Sync."""
    # ── Agent Missions data ──
    recent_runs = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.workflow_name == "agent_mission")
        .order_by(WorkflowRun.queued_at.desc())
        .limit(20)
        .all()
    )

    # ── Scheduler state ──
    scheduler = get_scheduler()
    scheduler_status = scheduler.get_status()

    # ── Discovery data ──
    total_discovered = db.query(func.count(DiscoveredTool.id)).scalar() or 0
    pending_review = db.query(func.count(DiscoveredTool.id)).filter(
        DiscoveredTool.status == "pending_review"
    ).scalar() or 0
    approved = db.query(func.count(DiscoveredTool.id)).filter(
        DiscoveredTool.status == "approved"
    ).scalar() or 0
    rejected = db.query(func.count(DiscoveredTool.id)).filter(
        DiscoveredTool.status == "rejected"
    ).scalar() or 0

    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    new_this_week = db.query(func.count(DiscoveredTool.id)).filter(
        DiscoveredTool.discovered_at >= week_ago
    ).scalar() or 0

    discovery_recent_runs = db.query(DiscoveryRun).order_by(
        desc(DiscoveryRun.started_at)
    ).limit(10).all()

    running_discovery = db.query(DiscoveryRun).filter(
        DiscoveryRun.status == "running"
    ).first()

    source_breakdown = db.query(
        DiscoveredTool.source_type,
        func.count(DiscoveredTool.id).label("count")
    ).group_by(DiscoveredTool.source_type).all()

    discovery_stats = {
        "total_discovered": total_discovered,
        "pending_review": pending_review,
        "approved": approved,
        "rejected": rejected,
        "new_this_week": new_this_week,
        "source_breakdown": dict(source_breakdown),
    }

    # ── GROUNDED Sync data ──
    from app.grounded_adapter import is_grounded_initialized
    from app.services.directory_sync import get_directory_sync_service

    org_count = db.query(func.count(MediaOrganization.id)).scalar() or 0
    journalist_count = db.query(func.count(Journalist.id)).scalar() or 0
    engagement_count = db.query(func.count(Engagement.id)).scalar() or 0

    grounded_initialized = is_grounded_initialized()
    kb_stats = {}
    if grounded_initialized:
        try:
            sync_service = get_directory_sync_service()
            kb_stats = sync_service.get_stats()
        except Exception as e:
            kb_stats = {"error": str(e)}

    sync_stats = {
        "organizations": org_count,
        "journalists": journalist_count,
        "engagements": engagement_count,
    }

    # Validate tab
    active_tab = tab if tab in ("missions", "discovery", "sync") else "missions"

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/agent/dashboard.html",
        {
            "request": request,
            "user": user,
            "active_admin_page": "agent",
            "active_tab": active_tab,
            # Agent
            "missions": MISSIONS,
            "recent_runs": recent_runs,
            "scheduler_status": scheduler_status,
            # Discovery
            "discovery_stats": discovery_stats,
            "discovery_recent_runs": discovery_recent_runs,
            "running_discovery": running_discovery,
            # Sync
            "sync_stats": sync_stats,
            "grounded_initialized": grounded_initialized,
            "kb_stats": kb_stats,
            **admin_context,
        },
    )


# ---------------------------------------------------------------------------
# Launch mission
# ---------------------------------------------------------------------------

@router.post("/launch")
async def launch_mission(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Launch an agent mission. Returns the run_id for status polling."""
    body = await request.json()
    mission_name = body.get("mission")
    params = body.get("params", {})

    if mission_name not in MISSIONS:
        raise HTTPException(status_code=400, detail=f"Unknown mission: {mission_name}")

    # Rate limit check
    allowed, retry_after, reason = check_workflow_rate_limit(
        "agent_mission", str(user.id)
    )
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "retry_after": retry_after,
                "reason": reason,
            },
        )

    # Create workflow run
    runtime = WorkflowRuntime(db)
    run = runtime.create_run(
        workflow_name="agent_mission",
        inputs={"mission": mission_name, "params": params},
        triggered_by=user.id,
        tags=["agent", mission_name],
    )

    # Launch agent in background
    asyncio.create_task(_run_agent(str(run.id), mission_name, params, db))

    return JSONResponse(content={"run_id": str(run.id), "status": "queued"})


async def _run_agent(run_id: str, mission_name: str, params: dict, db: Session):
    """Background task that executes the agent and updates the WorkflowRun."""
    from app.db import SessionLocal

    # Use a fresh DB session for the background task
    bg_db = SessionLocal()
    try:
        runtime = WorkflowRuntime(bg_db)
        run = runtime.get_run(UUID(run_id))
        if not run:
            logger.error(f"Agent run {run_id} not found")
            return

        runtime.update_status(run, status="running")

        engine = AgentEngine(bg_db)
        result = await engine.run(mission_name, params, run_id)

        # Quality judging
        quality_report = None
        if result.created_records:
            try:
                quality_report = await judge_mission_results(
                    bg_db, run_id, result.created_records
                )
            except Exception as e:
                logger.error(f"Quality judging error for run {run_id}: {e}")

        if result.error:
            runtime.update_status(
                run,
                status="failed",
                error_message=result.error,
                outputs={
                    "created_records": result.created_records,
                    "steps_taken": result.steps_taken,
                    "quality_report": quality_report,
                },
            )
        else:
            # Mark as needs_review so admin can approve records
            status = "needs_review" if result.created_records else "completed"
            outputs = {
                "created_records": result.created_records,
                "research_notes": result.research_notes[:5000],
                "steps_taken": result.steps_taken,
            }
            if quality_report:
                outputs["quality_report"] = quality_report
            runtime.update_status(
                run,
                status=status,
                outputs=outputs,
                review_required="Approve agent-created records" if result.created_records else None,
            )

    except Exception as e:
        logger.exception(f"Agent background task error for run {run_id}")
        try:
            runtime = WorkflowRuntime(bg_db)
            run = runtime.get_run(UUID(run_id))
            if run:
                runtime.update_status(run, status="failed", error_message=str(e))
        except Exception:
            pass
    finally:
        bg_db.close()


# ---------------------------------------------------------------------------
# Status polling
# ---------------------------------------------------------------------------

@router.get("/status/{run_id}")
async def mission_status(
    run_id: str,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get the current status of an agent mission."""
    try:
        run = db.query(WorkflowRun).filter(WorkflowRun.id == UUID(run_id)).first()
    except (ValueError, Exception):
        raise HTTPException(status_code=400, detail="Invalid run ID")

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return JSONResponse(content={
        "run_id": str(run.id),
        "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "error_message": run.error_message,
        "outputs": run.outputs or {},
    })


# ---------------------------------------------------------------------------
# Results page
# ---------------------------------------------------------------------------

@router.get("/results/{run_id}", response_class=HTMLResponse)
async def mission_results(
    request: Request,
    run_id: str,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """View detailed results and review records for an agent mission."""
    try:
        run = db.query(WorkflowRun).filter(WorkflowRun.id == UUID(run_id)).first()
    except (ValueError, Exception):
        raise HTTPException(status_code=400, detail="Invalid run ID")

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Fetch actual DB records created by this run
    draft_orgs = (
        db.query(MediaOrganization)
        .filter(MediaOrganization.notes.ilike(f"%run_id={run_id}%"))
        .all()
    )
    pending_tools = (
        db.query(DiscoveredTool)
        .filter(DiscoveredTool.source_name.ilike(f"%{run_id}%"))
        .all()
    )

    # Fetch use cases created by this run (tracked via source_name)
    pending_use_cases = (
        db.query(UseCase)
        .filter(UseCase.source_name.ilike(f"%{run_id}%"))
        .all()
    )

    # Fetch content items (legal frameworks, ethics policies) created by this run
    created_records = (run.outputs or {}).get("created_records", [])
    content_record_names = [
        r["name"] for r in created_records
        if r.get("tool") in ("create_legal_framework_content", "create_ethics_policy_content")
    ]
    pending_content = (
        db.query(ContentItem)
        .filter(
            ContentItem.tags.contains(["agent-generated"]),
            ContentItem.title.in_(content_record_names),
        )
        .all()
    ) if content_record_names else []

    return templates.TemplateResponse(
        "admin/agent/review.html",
        {
            "request": request,
            "user": user,
            "active_admin_page": "agent",
            "run": run,
            "run_id": run_id,
            "draft_orgs": draft_orgs,
            "pending_tools": pending_tools,
            "pending_use_cases": pending_use_cases,
            "pending_content": pending_content,
        },
    )


# ---------------------------------------------------------------------------
# Approve records from a run
# ---------------------------------------------------------------------------

@router.post("/approve/{run_id}")
async def approve_run_records(
    run_id: str,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Approve all draft organizations created by an agent run.

    Tools are reviewed via the Discovery pipeline, not here.
    """
    try:
        run = db.query(WorkflowRun).filter(WorkflowRun.id == UUID(run_id)).first()
    except (ValueError, Exception):
        raise HTTPException(status_code=400, detail="Invalid run ID")

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Only approve organizations — tools go through Discovery
    approved_count = 0
    orgs = (
        db.query(MediaOrganization)
        .filter(
            MediaOrganization.is_active == False,
            MediaOrganization.notes.ilike(f"%run_id={run_id}%"),
        )
        .all()
    )
    for org in orgs:
        org.is_active = True
        approved_count += 1

    # Count tools still pending in Discovery
    tools_pending = (
        db.query(DiscoveredTool)
        .filter(
            DiscoveredTool.status == "pending_review",
            DiscoveredTool.source_name.ilike(f"%{run_id}%"),
        )
        .count()
    )

    # Update workflow run status
    run.status = "completed"
    run.review_decision = "approved"
    run.reviewed_by = user.id
    from datetime import datetime, timezone
    run.reviewed_at = datetime.now(timezone.utc)
    run.completed_at = datetime.now(timezone.utc)

    db.commit()

    return JSONResponse(content={
        "status": "approved",
        "approved_count": approved_count,
        "tools_pending_in_discovery": tools_pending,
    })


# ---------------------------------------------------------------------------
# Approve / reject individual records
# ---------------------------------------------------------------------------

@router.post("/record/{record_type}/{record_id}/{action}")
async def update_record(
    record_type: str,
    record_id: int,
    action: str,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Approve or reject an individual agent-created record."""
    if action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")

    if record_type == "organization":
        record = db.query(MediaOrganization).filter(MediaOrganization.id == record_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="Organization not found")
        if action == "approve":
            record.is_active = True
        else:
            db.delete(record)

    elif record_type == "tool":
        if action == "approve":
            raise HTTPException(status_code=400, detail="Tools should be reviewed in Discovery")
        record = db.query(DiscoveredTool).filter(DiscoveredTool.id == record_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="Tool not found")
        record.status = "rejected"
        record.reviewed_by = user.id

    else:
        raise HTTPException(status_code=400, detail="Invalid record type")

    db.commit()
    return JSONResponse(content={"status": action + "d", "record_type": record_type, "record_id": record_id})


# ---------------------------------------------------------------------------
# Scheduler API endpoints
# ---------------------------------------------------------------------------

@router.get("/scheduler/status")
async def scheduler_status(
    user: User = Depends(require_admin),
):
    """Return full scheduler state for dashboard polling."""
    scheduler = get_scheduler()
    return JSONResponse(content=scheduler.get_status())


@router.post("/scheduler/start")
async def scheduler_start(
    user: User = Depends(require_admin),
):
    """Start the scheduler loop."""
    scheduler = get_scheduler()
    if scheduler.state == "running":
        return JSONResponse(content={"status": "already_running"})
    await scheduler.start()
    return JSONResponse(content={"status": "started"})


@router.post("/scheduler/stop")
async def scheduler_stop(
    user: User = Depends(require_admin),
):
    """Stop the scheduler (finishes current mission first)."""
    scheduler = get_scheduler()
    scheduler.stop()
    return JSONResponse(content={"status": "stopping"})


@router.post("/scheduler/pause")
async def scheduler_pause(
    user: User = Depends(require_admin),
):
    """Toggle pause/resume on the scheduler."""
    scheduler = get_scheduler()
    if scheduler.state == "paused":
        scheduler.resume()
        return JSONResponse(content={"status": "resumed"})
    elif scheduler.state == "running":
        scheduler.pause()
        return JSONResponse(content={"status": "paused"})
    return JSONResponse(content={"status": scheduler.state})


@router.post("/scheduler/config")
async def scheduler_config(
    request: Request,
    user: User = Depends(require_admin),
):
    """Update the scheduler schedule and delay."""
    body = await request.json()
    scheduler = get_scheduler()

    reset = body.get("reset_default", False)
    new_schedule = body.get("schedule")
    delay = body.get("delay_between_missions")

    if reset:
        from app.workflows.agent.scheduler import DEFAULT_SCHEDULE
        scheduler.update_schedule(list(DEFAULT_SCHEDULE), delay)
    elif new_schedule is not None:
        scheduler.update_schedule(new_schedule, delay)
    elif delay is not None:
        scheduler.delay_between_missions = delay

    return JSONResponse(content={"status": "updated", "schedule_count": len(scheduler.schedule)})


@router.get("/scheduler/activity")
async def scheduler_activity(
    user: User = Depends(require_admin),
):
    """Return recent activity log entries."""
    scheduler = get_scheduler()
    return JSONResponse(content={"activity": scheduler.get_activity()})
