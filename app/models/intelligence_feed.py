"""Intelligence Feed models — curated AI developments and updates."""
import uuid
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, Float,
    ForeignKey, CheckConstraint, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base


class FeedItem(Base):
    """A curated intelligence feed item.

    Items surface relevant developments in AI ethics, data law,
    security vulnerabilities, governance frameworks, and tool updates.
    """

    __tablename__ = "feed_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Identification
    title = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)

    # Content
    summary = Column(Text, nullable=True)
    content_markdown = Column(Text, nullable=True)

    # Classification
    feed_category = Column(String, nullable=False, index=True)
    # Categories: regulation, ethics, security, tool_update, sector_news, platform_update

    # Source
    source_url = Column(String, nullable=True)
    source_name = Column(String, nullable=True)

    # Scope
    jurisdiction = Column(String, nullable=True)  # eu, uk, us, global
    sectors = Column(JSONB, nullable=True, default=list)
    tags = Column(JSONB, nullable=True, default=list)

    # Ranking
    relevance_score = Column(Float, nullable=True, default=0.5)  # 0.0-1.0

    # Publishing
    published_at = Column(DateTime(timezone=True), nullable=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, nullable=False, default="draft", index=True)
    # Statuses: draft, published, archived

    # Generation
    generated_by_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("brain_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
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
            "feed_category IN ('regulation', 'ethics', 'security', 'tool_update', 'sector_news', 'platform_update')",
            name="ck_feed_items_category",
        ),
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_feed_items_status",
        ),
    )

    def __repr__(self):
        return f"<FeedItem {self.slug} [{self.feed_category}]>"


class UserFeedRead(Base):
    """Tracks which feed items a user has read."""

    __tablename__ = "user_feed_reads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    feed_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("feed_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    read_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "feed_item_id", name="uq_user_feed_read"),
    )
