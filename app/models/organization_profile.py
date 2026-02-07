"""Organization Profile model for platform user organizations.

This is distinct from MediaOrganization (journalist CRM directory).
OrganizationProfile represents the organizations that platform users belong to.
Each user can belong to exactly one organization.
"""
from sqlalchemy import Column, String, DateTime, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import re

from app.db import Base


class OrganizationProfile(Base):
    """An organization that platform users belong to.

    Created by admin. Users are assigned to exactly one org on creation.
    """
    __tablename__ = "organization_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Identity
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True, index=True)

    # Details
    country = Column(String, nullable=True)
    jurisdiction = Column(String, nullable=True)
    sector = Column(String, nullable=True)  # newsroom, ngo, academic, government, other
    size = Column(String, nullable=True)  # small, medium, large, enterprise
    risk_tolerance = Column(String, nullable=True)  # low, medium, high
    description = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    users = relationship("User", back_populates="organization_profile")

    __table_args__ = (
        CheckConstraint(
            "sector IN ('newsroom', 'ngo', 'academic', 'government', 'freelance', 'other')",
            name="ck_organization_profiles_sector",
        ),
        CheckConstraint(
            "size IN ('small', 'medium', 'large', 'enterprise')",
            name="ck_organization_profiles_size",
        ),
        CheckConstraint(
            "risk_tolerance IN ('low', 'medium', 'high')",
            name="ck_organization_profiles_risk_tolerance",
        ),
    )

    def __repr__(self):
        return f"<OrganizationProfile {self.slug} sector={self.sector}>"

    @staticmethod
    def generate_slug(name: str) -> str:
        """Generate a URL-safe slug from a name."""
        slug = name.lower()
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        slug = re.sub(r"[\s_]+", "-", slug)
        return slug.strip("-")[:100]
