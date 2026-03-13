"""Enhancement models: AuditScore and TimeDividendEntry."""
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Text, ForeignKey,
    UniqueConstraint, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db import Base


class AuditScore(Base):
    """User audit rubric score for a specific tool.

    Stores scores across the 4 audit dimensions:
    Data Sovereignty, Exportability, Business Model, Security.
    Each dimension is scored 0-5, total out of 20.
    """

    __tablename__ = "audit_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    tool_slug = Column(String(200), nullable=False, index=True)

    # 4 audit dimensions (each 0-5)
    data_sovereignty = Column(Integer, nullable=False)
    exportability = Column(Integer, nullable=False)
    business_model = Column(Integer, nullable=False)
    security = Column(Integer, nullable=False)

    # Computed total (0-20)
    total_score = Column(Integer, nullable=False)

    # Optional notes
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", backref="audit_scores")

    __table_args__ = (
        UniqueConstraint("user_id", "tool_slug", name="uq_audit_scores_user_tool"),
        CheckConstraint("data_sovereignty >= 0 AND data_sovereignty <= 5", name="ck_audit_sovereignty_range"),
        CheckConstraint("exportability >= 0 AND exportability <= 5", name="ck_audit_exportability_range"),
        CheckConstraint("business_model >= 0 AND business_model <= 5", name="ck_audit_business_model_range"),
        CheckConstraint("security >= 0 AND security <= 5", name="ck_audit_security_range"),
        CheckConstraint("total_score >= 0 AND total_score <= 20", name="ck_audit_total_range"),
    )


class TimeDividendEntry(Base):
    """User time dividend tracking entry per tool.

    Tracks estimated hours saved per week and how the user
    plans to reinvest that time.
    """

    __tablename__ = "time_dividend_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    tool_slug = Column(String(200), nullable=False, index=True)

    # Estimated hours saved per week
    hours_saved_weekly = Column(Float, nullable=False)

    # Reinvestment category
    reinvestment_category = Column(String(100), nullable=True)

    # Optional notes
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", backref="time_dividend_entries")

    __table_args__ = (
        UniqueConstraint("user_id", "tool_slug", name="uq_time_dividend_user_tool"),
        CheckConstraint("hours_saved_weekly >= 0", name="ck_time_dividend_hours_positive"),
    )
