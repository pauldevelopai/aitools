"""AI Readiness Assessment model."""
import uuid
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db import Base


class ReadinessAssessment(Base):
    """Records an AI readiness assessment result."""

    __tablename__ = "readiness_assessments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,  # nullable for anonymous lead-gen assessments
        index=True,
    )
    organisation_type = Column(String, nullable=True)

    # Raw answers: {question_id: selected_option_value, ...}
    answers = Column(JSONB, nullable=False)

    # Computed dimension scores: {awareness: 3.2, policy: 1.5, tools: 2.0, governance: 1.0, skills: 2.5}
    dimension_scores = Column(JSONB, nullable=False)

    # Overall score (1-5 scale)
    overall_score = Column(Float, nullable=False)

    # Maturity level derived from overall_score
    maturity_level = Column(String, nullable=False)

    # AI-generated recommendations (list of strings)
    recommendations = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
