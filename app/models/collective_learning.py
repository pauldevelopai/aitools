"""Collective Learning models — aggregated network insights."""
import uuid
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, Float,
    CheckConstraint, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db import Base


class NetworkInsight(Base):
    """Cached aggregate insight about the network.

    Insights are recomputed periodically from existing data
    (user activity, tools, lessons, readiness assessments, etc.).
    Only surfaced when sample_count >= 3 for anonymity.
    """

    __tablename__ = "network_insights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Classification
    insight_type = Column(String, nullable=False, index=True)
    # Types: tool_adoption, workflow_pattern, use_case_success,
    #        sector_trend, skill_growth

    # Content
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=True)
    detail_data = Column(JSONB, nullable=True, default=dict)

    # Scope (nullable = global)
    sector = Column(String, nullable=True, index=True)
    region = Column(String, nullable=True)

    # Anonymity gate
    sample_count = Column(Integer, nullable=False, default=0)

    # Time window
    period_start = Column(DateTime(timezone=True), nullable=True)
    period_end = Column(DateTime(timezone=True), nullable=True)

    # State
    calculated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "insight_type IN ('tool_adoption', 'workflow_pattern', 'use_case_success', 'sector_trend', 'skill_growth')",
            name="ck_network_insights_type",
        ),
        Index("ix_network_insights_active", "is_active", "insight_type"),
    )

    def __repr__(self):
        return f"<NetworkInsight {self.insight_type}: {self.title}>"
