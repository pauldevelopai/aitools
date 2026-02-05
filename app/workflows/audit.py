"""Audit logging utilities for workflow execution.

Provides centralized audit logging for all workflow operations using
the GROUNDED governance audit pattern.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from app.grounded_adapter import log_audit_event_compat

logger = logging.getLogger(__name__)


# Workflow-specific action types
class WorkflowAuditAction:
    """Constants for workflow audit action types."""
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    WORKFLOW_CANCELLED = "workflow_cancelled"
    WORKFLOW_RATE_LIMITED = "workflow_rate_limited"
    CONTENT_PUBLISHED = "content_published"
    CONTENT_UNPUBLISHED = "content_unpublished"
    CONTENT_APPROVED = "content_approved"
    CONTENT_REJECTED = "content_rejected"
    FRAMEWORK_STATUS_CHANGED = "framework_status_changed"
    TOOL_TEST_STARTED = "tool_test_started"
    TOOL_TEST_COMPLETED = "tool_test_completed"
    ENRICHMENT_APPROVED = "enrichment_approved"
    ENRICHMENT_REJECTED = "enrichment_rejected"


def log_workflow_event(
    action: str,
    workflow_name: str,
    workflow_run_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    actor_email: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    outcome: str = "success",
    details: Optional[dict[str, Any]] = None,
    error_message: Optional[str] = None,
) -> None:
    """Log a workflow-related audit event.

    Args:
        action: The action being performed (use WorkflowAuditAction constants)
        workflow_name: Name of the workflow (e.g., "partner_intelligence", "mentor_intake")
        workflow_run_id: ID of the workflow run if applicable
        actor_id: ID of the user who triggered the action
        actor_email: Email of the user for easier identification
        resource_type: Type of resource affected (e.g., "organization", "engagement", "framework")
        resource_id: ID of the resource affected
        outcome: "success", "failure", or "error"
        details: Additional context about the event
        error_message: Error message if action failed
    """
    event_details = {
        "workflow_name": workflow_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if workflow_run_id:
        event_details["workflow_run_id"] = workflow_run_id
    if actor_email:
        event_details["actor_email"] = actor_email
    if resource_type:
        event_details["resource_type"] = resource_type
    if resource_id:
        event_details["resource_id"] = resource_id
    if error_message:
        event_details["error_message"] = error_message
    if details:
        event_details.update(details)

    # Build resource string
    resource = f"workflow:{workflow_name}"
    if resource_type and resource_id:
        resource = f"{resource_type}:{resource_id}"

    # Log via GROUNDED audit system
    try:
        log_audit_event_compat(
            action=action,
            actor=actor_id or "system",
            resource=resource,
            outcome=outcome,
            details=event_details,
        )
    except Exception as e:
        # Don't let audit failures crash the application
        logger.warning(f"Failed to log audit event: {e}")

    # Also log to standard Python logger for immediate visibility
    log_level = logging.INFO if outcome == "success" else logging.WARNING
    logger.log(
        log_level,
        f"Workflow audit: {action} - {workflow_name} - {outcome}",
        extra={"audit_details": event_details}
    )


def log_workflow_start(
    workflow_name: str,
    workflow_run_id: str,
    actor_id: Optional[str] = None,
    actor_email: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    inputs_summary: Optional[dict] = None,
) -> None:
    """Log workflow start event."""
    log_workflow_event(
        action=WorkflowAuditAction.WORKFLOW_STARTED,
        workflow_name=workflow_name,
        workflow_run_id=workflow_run_id,
        actor_id=actor_id,
        actor_email=actor_email,
        resource_type=resource_type,
        resource_id=resource_id,
        outcome="success",
        details={"inputs_summary": inputs_summary} if inputs_summary else None,
    )


def log_workflow_complete(
    workflow_name: str,
    workflow_run_id: str,
    actor_id: Optional[str] = None,
    outputs_summary: Optional[dict] = None,
    duration_seconds: Optional[float] = None,
) -> None:
    """Log workflow completion event."""
    details = {}
    if outputs_summary:
        details["outputs_summary"] = outputs_summary
    if duration_seconds is not None:
        details["duration_seconds"] = round(duration_seconds, 2)

    log_workflow_event(
        action=WorkflowAuditAction.WORKFLOW_COMPLETED,
        workflow_name=workflow_name,
        workflow_run_id=workflow_run_id,
        actor_id=actor_id,
        outcome="success",
        details=details if details else None,
    )


def log_workflow_failure(
    workflow_name: str,
    workflow_run_id: str,
    error_message: str,
    actor_id: Optional[str] = None,
) -> None:
    """Log workflow failure event."""
    log_workflow_event(
        action=WorkflowAuditAction.WORKFLOW_FAILED,
        workflow_name=workflow_name,
        workflow_run_id=workflow_run_id,
        actor_id=actor_id,
        outcome="failure",
        error_message=error_message,
    )


def log_content_action(
    action: str,
    content_id: str,
    content_title: str,
    actor_id: str,
    actor_email: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    """Log content publish/unpublish/approve/reject actions."""
    log_workflow_event(
        action=action,
        workflow_name="content_management",
        resource_type="content_item",
        resource_id=content_id,
        actor_id=actor_id,
        actor_email=actor_email,
        outcome="success",
        details={"content_title": content_title, **(details or {})},
    )


def log_rate_limit_hit(
    workflow_name: str,
    actor_id: str,
    actor_email: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
) -> None:
    """Log when a workflow trigger is rate limited."""
    log_workflow_event(
        action=WorkflowAuditAction.WORKFLOW_RATE_LIMITED,
        workflow_name=workflow_name,
        actor_id=actor_id,
        actor_email=actor_email,
        resource_type=resource_type,
        resource_id=resource_id,
        outcome="blocked",
        details={"reason": "rate_limit_exceeded"},
    )
