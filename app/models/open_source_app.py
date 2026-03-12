"""Open Source App Directory models."""
import uuid
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text,
    ForeignKey, CheckConstraint, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base


class OpenSourceApp(Base):
    """A curated open-source application in the directory.

    Represents a self-hostable or downloadable open-source tool
    with installation guides, system requirements, and platform info.
    """

    __tablename__ = "open_source_apps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Identification
    slug = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    # Links
    github_url = Column(String, nullable=False)
    website_url = Column(String, nullable=True)
    docs_url = Column(String, nullable=True)

    # Classification
    categories = Column(JSONB, nullable=True, default=list)
    tags = Column(JSONB, nullable=True, default=list)
    sectors = Column(JSONB, nullable=True, default=list)

    # Technical details
    license_type = Column(String, nullable=False, default="MIT")
    deployment_type = Column(String, nullable=False, default="self_hosted", index=True)
    installation_guide = Column(Text, nullable=True)  # Markdown
    system_requirements = Column(Text, nullable=True)  # Markdown
    platforms = Column(JSONB, nullable=True, default=list)  # e.g. ["linux", "macos", "windows", "docker"]
    difficulty = Column(String, nullable=False, default="beginner")
    pricing_model = Column(String, nullable=False, default="free")

    # Popularity & quality
    github_stars = Column(Integer, nullable=True)
    community_rating = Column(Float, nullable=True)  # 0.0 - 5.0
    last_verified_at = Column(DateTime(timezone=True), nullable=True)

    # Display
    is_featured = Column(Boolean, nullable=False, default=False)
    status = Column(String, nullable=False, default="draft", index=True)

    # Creator
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
            "deployment_type IN ('self_hosted', 'cloud', 'hybrid', 'desktop')",
            name="ck_open_source_apps_deployment_type",
        ),
        CheckConstraint(
            "difficulty IN ('beginner', 'intermediate', 'advanced')",
            name="ck_open_source_apps_difficulty",
        ),
        CheckConstraint(
            "pricing_model IN ('free', 'freemium', 'open_core')",
            name="ck_open_source_apps_pricing_model",
        ),
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_open_source_apps_status",
        ),
        CheckConstraint(
            "community_rating IS NULL OR (community_rating >= 0 AND community_rating <= 5)",
            name="ck_open_source_apps_community_rating",
        ),
        Index("ix_open_source_apps_created_by", "created_by"),
        Index("ix_open_source_apps_is_featured", "is_featured"),
        Index("ix_open_source_apps_difficulty", "difficulty"),
        Index("ix_open_source_apps_status_featured", "status", "is_featured"),
        Index("ix_open_source_apps_platforms_gin", "platforms", postgresql_using="gin"),
    )

    @staticmethod
    def generate_slug(name: str) -> str:
        """Generate a URL-safe slug from a name."""
        import re
        slug = name.lower().strip()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'[\s-]+', '-', slug)
        return slug.strip('-')

    def __repr__(self):
        return f"<OpenSourceApp {self.slug} [{self.deployment_type}]>"
