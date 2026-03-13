"""User tool installation tracking models."""
import uuid
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text,
    ForeignKey, UniqueConstraint, Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base


class UserToolInstallation(Base):
    """Tracks which tools a user has installed locally."""

    __tablename__ = "user_tool_installations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    app_id = Column(
        UUID(as_uuid=True),
        ForeignKey("open_source_apps.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Installation status
    status = Column(String, nullable=False, default="not_installed")  # not_installed, installed, failed
    installed_at = Column(DateTime(timezone=True), nullable=True)
    is_healthy = Column(Boolean, nullable=True)
    last_health_check = Column(DateTime(timezone=True), nullable=True)

    # User feedback
    user_rating = Column(Integer, nullable=True)  # 1-5
    user_notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    app = relationship("OpenSourceApp", foreign_keys=[app_id])

    __table_args__ = (
        UniqueConstraint("user_id", "app_id", name="uq_user_tool_installations_user_app"),
        Index("ix_user_tool_installations_user_id", "user_id"),
        Index("ix_user_tool_installations_app_id", "app_id"),
    )

    def __repr__(self):
        return f"<UserToolInstallation user={self.user_id} app={self.app_id} status={self.status}>"
