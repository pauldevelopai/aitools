"""Workflow run models for LangGraph workflow execution tracking."""
from sqlalchemy import (
    Column, String, DateTime, Text, ForeignKey, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db import Base


class WorkflowRun(Base):
    """Tracks workflow executions through the LangGraph runtime."""

    __tablename__ = "workflow_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Workflow identification
    workflow_name = Column(String, nullable=False, index=True)
    workflow_version = Column(String, nullable=True)  # Optional version tracking

    # Execution status
    status = Column(String, nullable=False, default="queued", index=True)
    # Status flow: queued → running → needs_review → completed → failed

    # Timestamps
    queued_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Input/Output data
    inputs = Column(JSONB, nullable=True, default=dict)
    outputs = Column(JSONB, nullable=True, default=dict)

    # State tracking for LangGraph checkpoints
    state = Column(JSONB, nullable=True, default=dict)

    # Error tracking
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)

    # Human-in-the-loop review
    review_required = Column(String, nullable=True)  # Reason review is needed
    reviewed_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_decision = Column(String, nullable=True)  # "approved", "rejected", "modified"

    # Metadata
    triggered_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    run_config = Column(JSONB, nullable=True, default=dict)  # Runtime configuration
    tags = Column(JSONB, nullable=True, default=list)  # For filtering/grouping runs

    # Standard timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    triggerer = relationship("User", foreign_keys=[triggered_by])
    reviewer = relationship("User", foreign_keys=[reviewed_by])

    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'needs_review', 'completed', 'failed', 'cancelled')",
            name='ck_workflow_run_status'
        ),
        CheckConstraint(
            "review_decision IS NULL OR review_decision IN ('approved', 'rejected', 'modified')",
            name='ck_workflow_run_review_decision'
        ),
    )

    def __repr__(self):
        return f"<WorkflowRun {self.id} workflow={self.workflow_name} status={self.status}>"
