"""User progress tracking model."""
import uuid
from sqlalchemy import Column, Boolean, Integer, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db import Base


class UserProgress(Base):
    """Tracks a user's AI implementation progress across platform features."""

    __tablename__ = "user_progress"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Completion flags
    ethics_policy_complete = Column(Boolean, nullable=False, server_default="false")
    legal_framework_complete = Column(Boolean, nullable=False, server_default="false")
    strategy_plan_complete = Column(Boolean, nullable=False, server_default="false")
    readiness_assessment_complete = Column(Boolean, nullable=False, server_default="false")

    # Counts
    tools_evaluated_count = Column(Integer, nullable=False, server_default="0")

    # Computed
    overall_completion_pct = Column(Float, nullable=False, server_default="0.0")

    # Timestamped log of completion events
    completed_items = Column(JSONB, nullable=False, server_default="[]")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
