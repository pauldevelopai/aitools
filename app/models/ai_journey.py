"""AI Journey tracking model for media organizations."""
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.db import Base


class AIJourneyEntry(Base):
    """Tracks an organization's progress through AI adoption stages."""

    __tablename__ = "ai_journey_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("media_organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    stage = Column(String(30), nullable=False)  # not_started, awareness, exploring, piloting, implementing, integrated, advanced
    notes = Column(Text)
    recorded_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    organization = relationship("MediaOrganization", back_populates="journey_entries")
    recorded_by = relationship("User")
