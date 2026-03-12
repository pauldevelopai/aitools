"""Brain models for self-improvement loop.

Tracks knowledge gaps, content quality, and Brain run audit trails.
"""
import uuid

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Text, Boolean,
    ForeignKey, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.db import Base


class KnowledgeGap(Base):
    """Tracks what the platform doesn't know well.

    Detected from low-similarity RAG queries, user feedback,
    admin flags, or content staleness checks.
    """
    __tablename__ = "knowledge_gaps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    topic = Column(String, nullable=False, index=True)
    sector = Column(String, nullable=True)  # newsroom, ngo, law_firm, business, general

    gap_type = Column(String, nullable=False, default="no_content")
    # no_content, low_quality, stale, user_requested

    detected_from = Column(String, nullable=False)
    # low_similarity, user_feedback, admin_flag, staleness_check

    detection_details = Column(JSONB, nullable=True)
    # e.g. {"query": "...", "similarity": 0.3, "user_id": "..."}

    priority = Column(Integer, nullable=False, default=3)
    # 1 (highest) to 5 (lowest)

    status = Column(String, nullable=False, default="open", index=True)
    # open, researching, filled, dismissed

    filled_by_content_id = Column(String, nullable=True)
    filled_by_run_id = Column(UUID(as_uuid=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "gap_type IN ('no_content', 'low_quality', 'stale', 'user_requested')",
            name="ck_knowledge_gap_type",
        ),
        CheckConstraint(
            "status IN ('open', 'researching', 'filled', 'dismissed')",
            name="ck_knowledge_gap_status",
        ),
        CheckConstraint(
            "priority BETWEEN 1 AND 5",
            name="ck_knowledge_gap_priority",
        ),
    )

    def __repr__(self):
        return f"<KnowledgeGap {self.id} topic='{self.topic}' status={self.status}>"


class ContentQualityScore(Base):
    """Tracks how well content performs.

    Updated on every RAG query (which chunks were used, similarity scores)
    and on every user feedback event.
    """
    __tablename__ = "content_quality_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    content_type = Column(String, nullable=False, index=True)
    # chunk, tool, use_case, resource, content_item

    content_id = Column(String, nullable=False, index=True)
    # ID of the content record

    positive_feedback_count = Column(Integer, nullable=False, default=0)
    negative_feedback_count = Column(Integer, nullable=False, default=0)

    avg_similarity_when_used = Column(Float, nullable=True)
    # Average cosine similarity when this content is retrieved via RAG

    times_cited = Column(Integer, nullable=False, default=0)
    # How many times this content was used in a RAG response

    last_used_at = Column(DateTime(timezone=True), nullable=True)

    staleness_score = Column(Float, nullable=False, default=0.0)
    # 0.0 = fresh, 1.0 = very stale. Based on age + source freshness

    overall_quality_score = Column(Float, nullable=False, default=0.5)
    # Composite score: feedback + similarity + staleness

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<ContentQualityScore {self.content_type}/{self.content_id} score={self.overall_quality_score}>"


class BrainRun(Base):
    """Audit trail for every Brain action.

    Stores the full tool call history and quality assessment
    for each Brain run.
    """
    __tablename__ = "brain_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    mission_type = Column(String, nullable=False, index=True)

    trigger = Column(String, nullable=False, default="admin")
    # scheduled, admin, gap_detected, user_feedback

    input_params = Column(JSONB, nullable=True)

    tool_calls = Column(JSONB, nullable=True, default=list)
    # Array of {tool, input, output, turn}

    records_created = Column(JSONB, nullable=True, default=list)
    # Array of {tool, record_type, record_id, name}

    quality_assessment = Column(JSONB, nullable=True)
    # Output of quality judging

    tokens_used = Column(JSONB, nullable=True)
    # {input: N, output: N}

    research_notes = Column(Text, nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    status = Column(String, nullable=False, default="running", index=True)
    # running, completed, failed

    error_message = Column(Text, nullable=True)

    # Link to workflow run if one exists
    workflow_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_runs.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'completed', 'failed')",
            name="ck_brain_run_status",
        ),
    )

    def __repr__(self):
        return f"<BrainRun {self.id} mission={self.mission_type} status={self.status}>"
