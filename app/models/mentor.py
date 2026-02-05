"""Mentor workflow models for tracking tasks and artifacts."""
from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, Integer, ForeignKey, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.db import Base


class MentorTask(Base):
    """Ticket-like task item tied to an Engagement.

    Tasks track the work items identified during mentoring sessions,
    forming a backlog that evolves through the prototype development process.
    """

    __tablename__ = "mentor_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Parent engagement
    engagement_id = Column(
        UUID(as_uuid=True),
        ForeignKey("engagements.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Task details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    task_type = Column(String(50), nullable=False, default="action")  # action, decision, blocker, learning, deliverable

    # Status tracking
    status = Column(String(50), nullable=False, default="pending")  # pending, in_progress, completed, deferred, cancelled
    priority = Column(Integer, nullable=False, default=2)  # 1=highest, 5=lowest

    # Assignment and ownership
    assigned_to = Column(String(255), nullable=True)  # Journalist name or "mentor"
    due_date = Column(DateTime(timezone=True), nullable=True)

    # Completion tracking
    completed_at = Column(DateTime(timezone=True), nullable=True)
    completion_notes = Column(Text, nullable=True)

    # Decision log (for decision-type tasks)
    decision_made = Column(Text, nullable=True)
    decision_rationale = Column(Text, nullable=True)

    # Workflow tracking
    created_by_workflow = Column(String(100), nullable=True)  # "intake", "pre_call", "post_call"
    workflow_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Ordering
    sort_order = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    engagement = relationship("Engagement", backref="mentor_tasks")
    workflow_run = relationship("WorkflowRun", backref="mentor_tasks")

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed', 'deferred', 'cancelled')",
            name='ck_mentor_task_status'
        ),
        CheckConstraint(
            "task_type IN ('action', 'decision', 'blocker', 'learning', 'deliverable')",
            name='ck_mentor_task_type'
        ),
        CheckConstraint(
            'priority >= 1 AND priority <= 5',
            name='ck_mentor_task_priority'
        ),
    )

    def __repr__(self):
        return f"<MentorTask {self.id} title={self.title[:30]}... status={self.status}>"


class MentorArtifact(Base):
    """Versioned artifact from mentor workflows.

    Artifacts include:
    - Prototype Charter (from intake/Session 0)
    - Session Agenda (from pre_call)
    - Prototype Pack (from post_call)
    - Decision Log (accumulated across sessions)
    """

    __tablename__ = "mentor_artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Parent engagement
    engagement_id = Column(
        UUID(as_uuid=True),
        ForeignKey("engagements.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Artifact identification
    artifact_type = Column(String(50), nullable=False)  # prototype_charter, session_agenda, prototype_pack, decision_log, transcript
    title = Column(String(500), nullable=False)

    # Versioning
    version = Column(Integer, nullable=False, default=1)
    is_current = Column(Boolean, nullable=False, default=True)

    # Content
    content = Column(Text, nullable=False)  # Markdown content
    content_format = Column(String(20), nullable=False, default="markdown")  # markdown, html, json

    # Structured data (for machine-readable parts)
    structured_data = Column(JSONB, nullable=True, default=dict)

    # Source tracking
    source_notes = Column(Text, nullable=True)  # Original notes/transcript that generated this
    source_file_url = Column(String(500), nullable=True)  # URL to uploaded file if applicable

    # Workflow tracking
    created_by_workflow = Column(String(100), nullable=True)  # "intake", "pre_call", "post_call"
    workflow_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    engagement = relationship("Engagement", backref="mentor_artifacts")
    workflow_run = relationship("WorkflowRun", backref="mentor_artifacts")

    __table_args__ = (
        CheckConstraint(
            "artifact_type IN ('prototype_charter', 'session_agenda', 'prototype_pack', 'decision_log', 'transcript', 'notes')",
            name='ck_mentor_artifact_type'
        ),
        CheckConstraint(
            "content_format IN ('markdown', 'html', 'json', 'text')",
            name='ck_mentor_artifact_format'
        ),
    )

    def __repr__(self):
        return f"<MentorArtifact {self.id} type={self.artifact_type} v{self.version}>"


class MentorSession(Base):
    """Tracks individual mentor sessions within an engagement.

    An engagement may have multiple sessions (Session 0, Session 1, etc.).
    This tracks the progression through the mentoring program.
    """

    __tablename__ = "mentor_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Parent engagement
    engagement_id = Column(
        UUID(as_uuid=True),
        ForeignKey("engagements.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Session identification
    session_number = Column(Integer, nullable=False, default=0)  # 0 = intake, 1+ = regular sessions
    session_type = Column(String(50), nullable=False, default="regular")  # intake, regular, review, final

    # Timing
    scheduled_date = Column(DateTime(timezone=True), nullable=True)
    actual_date = Column(DateTime(timezone=True), nullable=True)
    duration_minutes = Column(Integer, nullable=True)

    # Status
    status = Column(String(50), nullable=False, default="scheduled")  # scheduled, completed, cancelled, rescheduled

    # Notes and outcomes
    agenda = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    key_decisions = Column(JSONB, nullable=True, default=list)
    action_items = Column(JSONB, nullable=True, default=list)

    # Workflow tracking
    workflow_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    engagement = relationship("Engagement", backref="mentor_sessions")
    workflow_run = relationship("WorkflowRun", backref="mentor_sessions")

    __table_args__ = (
        CheckConstraint(
            "status IN ('scheduled', 'completed', 'cancelled', 'rescheduled')",
            name='ck_mentor_session_status'
        ),
        CheckConstraint(
            "session_type IN ('intake', 'regular', 'review', 'final')",
            name='ck_mentor_session_type'
        ),
    )

    def __repr__(self):
        return f"<MentorSession {self.id} #{self.session_number} status={self.status}>"
