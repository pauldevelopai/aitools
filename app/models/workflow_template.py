"""Workflow Template models — reusable multi-step AI workflows."""
import uuid
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text,
    ForeignKey, CheckConstraint, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base


class WorkflowTemplate(Base):
    """A reusable workflow template that users can start.

    Templates define multi-step AI workflows for real operational tasks
    such as fact-checking, policy drafting, or tool evaluation.
    """

    __tablename__ = "workflow_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Identification
    slug = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    # Classification
    category = Column(String, nullable=False, index=True)
    # Categories: content_production, research, governance, audience, operations

    # Steps definition: [{order, name, description, tool_or_action, config}]
    steps = Column(JSONB, nullable=False, default=list)

    # Input schema: what the user provides to start
    input_schema = Column(JSONB, nullable=True, default=dict)

    # Metadata
    estimated_minutes = Column(Integer, nullable=True)
    difficulty = Column(String, nullable=False, default="beginner")
    sectors = Column(JSONB, nullable=True, default=list)
    tags = Column(JSONB, nullable=True, default=list)

    # Usage tracking
    usage_count = Column(Integer, nullable=False, default=0)
    is_featured = Column(Boolean, nullable=False, default=False)

    # Status
    status = Column(String, nullable=False, default="draft", index=True)

    # Creator
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])

    __table_args__ = (
        CheckConstraint(
            "category IN ('content_production', 'research', 'governance', 'audience', 'operations')",
            name="ck_workflow_templates_category",
        ),
        CheckConstraint(
            "difficulty IN ('beginner', 'intermediate', 'advanced')",
            name="ck_workflow_templates_difficulty",
        ),
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_workflow_templates_status",
        ),
    )

    def __repr__(self):
        return f"<WorkflowTemplate {self.slug} [{self.category}]>"
