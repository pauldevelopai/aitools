"""Learning paths and user enrollment models."""
import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db import Base


class LearningPath(Base):
    """A structured learning journey chaining platform features."""

    __tablename__ = "learning_paths"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    sector = Column(String, nullable=True)  # newsroom/ngo/law_firm/business/None=all
    difficulty = Column(String, nullable=False, server_default="beginner")
    steps = Column(JSONB, nullable=False)  # [{id, title, description, action_type, action_url, order}]
    estimated_minutes = Column(Integer, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserPathEnrollment(Base):
    """Tracks a user's progress through a learning path."""

    __tablename__ = "user_path_enrollments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    path_id = Column(UUID(as_uuid=True), ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False, index=True)
    completed_steps = Column(JSONB, nullable=False, server_default="[]")
    completion_pct = Column(Float, nullable=False, server_default="0.0")
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "path_id", name="uq_user_path"),
    )
