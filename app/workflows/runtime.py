"""Workflow runtime for executing LangGraph workflows.

This module provides a consistent interface to:
- Run workflows by name
- Pass inputs and configuration
- Persist run status to the database
- Capture errors and state checkpoints
"""
import asyncio
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID
import traceback

from sqlalchemy.orm import Session

from app.models.workflow import WorkflowRun


class WorkflowRuntime:
    """Runtime for executing and managing LangGraph workflows.

    The runtime provides workflow execution with:
    - Status tracking: queued → running → needs_review → completed → failed
    - Input/output persistence
    - Error capture
    - State checkpointing for human-in-the-loop
    """

    # Registry of available workflows (to be populated by workflow definitions)
    _workflows: dict[str, Any] = {}

    def __init__(self, db: Session):
        """Initialize runtime with database session.

        Args:
            db: SQLAlchemy database session for persisting run state
        """
        self.db = db

    @classmethod
    def register_workflow(cls, name: str, workflow: Any, version: str | None = None) -> None:
        """Register a workflow for execution.

        Args:
            name: Unique name for the workflow
            workflow: LangGraph compiled graph or callable
            version: Optional version string
        """
        cls._workflows[name] = {
            "workflow": workflow,
            "version": version,
        }

    @classmethod
    def list_workflows(cls) -> list[str]:
        """List all registered workflow names."""
        return list(cls._workflows.keys())

    @classmethod
    def get_workflow(cls, name: str) -> Optional[dict]:
        """Get a registered workflow by name."""
        return cls._workflows.get(name)

    def create_run(
        self,
        workflow_name: str,
        inputs: dict | None = None,
        config: dict | None = None,
        triggered_by: UUID | None = None,
        tags: list[str] | None = None,
    ) -> WorkflowRun:
        """Create a new workflow run record.

        The run is created in 'queued' status. Call execute() to run it.

        Args:
            workflow_name: Name of the workflow to run
            inputs: Input data for the workflow
            config: Runtime configuration
            triggered_by: User ID who triggered the run
            tags: Optional tags for filtering

        Returns:
            The created WorkflowRun record
        """
        workflow_info = self._workflows.get(workflow_name)
        version = workflow_info["version"] if workflow_info else None

        run = WorkflowRun(
            workflow_name=workflow_name,
            workflow_version=version,
            status="queued",
            inputs=inputs or {},
            run_config=config or {},
            triggered_by=triggered_by,
            tags=tags or [],
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def get_run(self, run_id: UUID) -> WorkflowRun | None:
        """Get a workflow run by ID."""
        return self.db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()

    def update_status(
        self,
        run: WorkflowRun,
        status: str,
        error_message: str | None = None,
        outputs: dict | None = None,
        state: dict | None = None,
        review_required: str | None = None,
    ) -> WorkflowRun:
        """Update the status of a workflow run.

        Args:
            run: The workflow run to update
            status: New status value
            error_message: Error message if failed
            outputs: Output data if completed
            state: Current state checkpoint
            review_required: Reason if needs_review

        Returns:
            Updated WorkflowRun
        """
        run.status = status
        now = datetime.now(timezone.utc)

        if status == "running" and run.started_at is None:
            run.started_at = now
        elif status in ("completed", "failed", "cancelled"):
            run.completed_at = now

        if error_message:
            run.error_message = error_message
        if outputs is not None:
            run.outputs = outputs
        if state is not None:
            run.state = state
        if review_required:
            run.review_required = review_required

        self.db.commit()
        self.db.refresh(run)
        return run

    async def execute(self, run: WorkflowRun) -> WorkflowRun:
        """Execute a workflow run.

        This method:
        1. Validates the workflow exists
        2. Updates status to 'running'
        3. Executes the workflow
        4. Updates status to 'completed' or 'failed'

        Args:
            run: The workflow run to execute

        Returns:
            Updated WorkflowRun with results
        """
        workflow_info = self._workflows.get(run.workflow_name)

        if not workflow_info:
            return self.update_status(
                run,
                status="failed",
                error_message=f"Workflow '{run.workflow_name}' not found",
            )

        # Mark as running
        self.update_status(run, status="running")

        try:
            workflow = workflow_info["workflow"]

            # Execute the workflow (supports both sync and async)
            if hasattr(workflow, "ainvoke"):
                # LangGraph async execution
                result = await workflow.ainvoke(run.inputs, config=run.run_config)
            elif hasattr(workflow, "invoke"):
                # LangGraph sync execution
                result = workflow.invoke(run.inputs, config=run.run_config)
            elif callable(workflow):
                # Simple callable
                result = await workflow(run.inputs, config=run.run_config) if asyncio.iscoroutinefunction(workflow) else workflow(run.inputs, config=run.run_config)
            else:
                raise ValueError(f"Workflow '{run.workflow_name}' is not executable")

            # Handle result
            if isinstance(result, dict):
                outputs = result
                state = result.get("__state__", {})
            else:
                outputs = {"result": result}
                state = {}

            # Check if review is needed
            if state.get("needs_review"):
                return self.update_status(
                    run,
                    status="needs_review",
                    outputs=outputs,
                    state=state,
                    review_required=state.get("review_reason", "Manual review required"),
                )

            return self.update_status(
                run,
                status="completed",
                outputs=outputs,
                state=state,
            )

        except Exception as e:
            run.error_traceback = traceback.format_exc()
            return self.update_status(
                run,
                status="failed",
                error_message=str(e),
            )

    def submit_review(
        self,
        run: WorkflowRun,
        decision: str,
        reviewer_id: UUID,
        modified_state: dict | None = None,
    ) -> WorkflowRun:
        """Submit a review decision for a run in needs_review status.

        Args:
            run: The workflow run to review
            decision: "approved", "rejected", or "modified"
            reviewer_id: User ID of the reviewer
            modified_state: If decision is "modified", the updated state

        Returns:
            Updated WorkflowRun
        """
        if run.status != "needs_review":
            raise ValueError(f"Run is not awaiting review (status: {run.status})")

        run.review_decision = decision
        run.reviewed_by = reviewer_id
        run.reviewed_at = datetime.now(timezone.utc)

        if decision == "approved":
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
        elif decision == "rejected":
            run.status = "failed"
            run.completed_at = datetime.now(timezone.utc)
            run.error_message = "Rejected during review"
        elif decision == "modified" and modified_state:
            run.state = modified_state
            # Keep in needs_review or move to running for re-execution
            # depending on workflow design

        self.db.commit()
        self.db.refresh(run)
        return run


# Convenience functions for simpler usage

def run_workflow(
    db: Session,
    workflow_name: str,
    inputs: dict | None = None,
    config: dict | None = None,
    triggered_by: UUID | None = None,
    tags: list[str] | None = None,
) -> WorkflowRun:
    """Create a workflow run record (does not execute).

    Use this to queue a workflow for later execution.

    Args:
        db: Database session
        workflow_name: Name of the workflow
        inputs: Input data
        config: Runtime configuration
        triggered_by: User ID
        tags: Optional tags

    Returns:
        Created WorkflowRun in 'queued' status
    """
    runtime = WorkflowRuntime(db)
    return runtime.create_run(
        workflow_name=workflow_name,
        inputs=inputs,
        config=config,
        triggered_by=triggered_by,
        tags=tags,
    )


def get_workflow_status(db: Session, run_id: UUID) -> dict | None:
    """Get the current status of a workflow run.

    Args:
        db: Database session
        run_id: The run ID to check

    Returns:
        Dict with status info or None if not found
    """
    runtime = WorkflowRuntime(db)
    run = runtime.get_run(run_id)
    if not run:
        return None

    return {
        "id": str(run.id),
        "workflow_name": run.workflow_name,
        "status": run.status,
        "queued_at": run.queued_at.isoformat() if run.queued_at else None,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "error_message": run.error_message,
        "review_required": run.review_required,
    }


def get_workflows_health() -> dict:
    """Check the health of the workflows subsystem.

    Similar to get_grounded_health(), this verifies:
    - LangChain/LangGraph imports work
    - Registered workflows are available

    Returns:
        Dict with health status
    """
    health_info = {
        "status": "healthy",
        "langchain_available": False,
        "langgraph_available": False,
        "registered_workflows": [],
        "errors": [],
    }

    # Check LangChain
    try:
        import langchain
        health_info["langchain_available"] = True
        health_info["langchain_version"] = langchain.__version__
    except ImportError as e:
        health_info["errors"].append(f"LangChain import failed: {e}")
        health_info["status"] = "degraded"

    # Check LangGraph
    try:
        import langgraph
        health_info["langgraph_available"] = True
        health_info["langgraph_version"] = getattr(langgraph, "__version__", "unknown")
    except ImportError as e:
        health_info["errors"].append(f"LangGraph import failed: {e}")
        health_info["status"] = "degraded"

    # List registered workflows
    health_info["registered_workflows"] = WorkflowRuntime.list_workflows()

    # If both imports failed, mark as unhealthy
    if not health_info["langchain_available"] and not health_info["langgraph_available"]:
        health_info["status"] = "unhealthy"

    return health_info
