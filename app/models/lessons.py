"""Micro-lessons gamification models."""
import uuid
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, Float,
    ForeignKey, UniqueConstraint, CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db import Base


class LessonModule(Base):
    """A group of lessons forming a learning module."""

    __tablename__ = "lesson_modules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    sector = Column(String, nullable=True)  # newsroom/ngo/law_firm/business/None=all
    difficulty = Column(String, nullable=False, server_default="beginner")
    order = Column(Integer, nullable=False, server_default="1")
    icon = Column(String, nullable=True)
    prerequisites = Column(JSONB, nullable=True, server_default="[]")  # list of module slugs
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Lesson(Base):
    """An individual teaching unit within a module."""

    __tablename__ = "lessons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module_id = Column(
        UUID(as_uuid=True),
        ForeignKey("lesson_modules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slug = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    content_markdown = Column(Text, nullable=False)
    learning_objectives = Column(JSONB, nullable=False, server_default="[]")
    task_type = Column(String, nullable=False, server_default="action")
    task_prompt = Column(Text, nullable=False)
    task_hints = Column(JSONB, nullable=True)
    verification_type = Column(String, nullable=False, server_default="self_report")
    token_reward = Column(Integer, nullable=False, server_default="1")
    order = Column(Integer, nullable=False, server_default="1")
    estimated_minutes = Column(Integer, nullable=True)
    generated_by_run_id = Column(String, nullable=True)
    status = Column(String, nullable=False, server_default="draft")

    # Cross-references to platform content
    related_app_slugs = Column(JSONB, nullable=True, server_default="[]")   # open_source_apps slugs
    related_tool_slugs = Column(JSONB, nullable=True, server_default="[]")  # discovered_tools slugs

    # Adaptive difficulty
    recommended_level = Column(String, nullable=True)  # beginner/intermediate/advanced
    sector_relevance = Column(JSONB, nullable=True, server_default="[]")  # e.g. ["newsroom","ngo"]

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "task_type IN ('action', 'reflection', 'quiz', 'exploration')",
            name="ck_lesson_task_type",
        ),
        CheckConstraint(
            "verification_type IN ('self_report', 'ai_review')",
            name="ck_lesson_verification_type",
        ),
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_lesson_status",
        ),
        CheckConstraint(
            "recommended_level IS NULL OR recommended_level IN ('beginner', 'intermediate', 'advanced')",
            name="ck_lesson_recommended_level",
        ),
    )


class UserLessonProgress(Base):
    """Tracks a user's progress on an individual lesson."""

    __tablename__ = "user_lesson_progress"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lesson_id = Column(
        UUID(as_uuid=True),
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(String, nullable=False, server_default="started")
    task_response = Column(Text, nullable=True)
    ai_feedback = Column(Text, nullable=True)
    tokens_awarded = Column(Integer, nullable=False, server_default="0")
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "lesson_id", name="uq_user_lesson"),
    )


class UserTokens(Base):
    """Per-user gamification state: token balance, streaks, level."""

    __tablename__ = "user_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    balance = Column(Integer, nullable=False, server_default="0")
    total_earned = Column(Integer, nullable=False, server_default="0")
    current_streak = Column(Integer, nullable=False, server_default="0")
    longest_streak = Column(Integer, nullable=False, server_default="0")
    last_completed_at = Column(DateTime(timezone=True), nullable=True)
    level = Column(Integer, nullable=False, server_default="1")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class TokenTransaction(Base):
    """Audit trail for token awards and spends."""

    __tablename__ = "token_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount = Column(Integer, nullable=False)
    transaction_type = Column(String, nullable=False)
    reference_id = Column(String, nullable=True)
    description = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
