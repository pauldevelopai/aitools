"""Data Asset Registry models — collective data licensing and management."""
import uuid
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, Date,
    ForeignKey, CheckConstraint, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base


class DataAsset(Base):
    """A registered data asset in the collective registry.

    Organisations register their data assets (archives, datasets, feeds)
    for discovery and potential licensing by other network members.
    """

    __tablename__ = "data_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Identification
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Ownership
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Classification
    asset_type = Column(String, nullable=False, index=True)
    # Types: archive, dataset, api, feed, document_collection

    data_format = Column(String, nullable=True)  # pdf, csv, json, html
    record_count = Column(Integer, nullable=True)  # approximate size

    # Temporal coverage
    date_range_start = Column(Date, nullable=True)
    date_range_end = Column(Date, nullable=True)

    # Metadata
    languages = Column(JSONB, nullable=True, default=list)  # ["en", "fr", "sw"]
    sectors = Column(JSONB, nullable=True, default=list)
    tags = Column(JSONB, nullable=True, default=list)

    # Classification / access
    classification = Column(String, nullable=False, default="internal")
    # Levels: public, internal, confidential

    # Licensing
    is_licensable = Column(Boolean, nullable=False, default=False)
    licensing_terms = Column(Text, nullable=True)
    contact_email = Column(String, nullable=True)

    # Status
    status = Column(String, nullable=False, default="draft", index=True)
    # Statuses: draft, active, archived

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    inquiries = relationship("LicenseInquiry", back_populates="asset", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "asset_type IN ('archive', 'dataset', 'api', 'feed', 'document_collection')",
            name="ck_data_assets_type",
        ),
        CheckConstraint(
            "classification IN ('public', 'internal', 'confidential')",
            name="ck_data_assets_classification",
        ),
        CheckConstraint(
            "status IN ('draft', 'active', 'archived')",
            name="ck_data_assets_status",
        ),
    )

    def __repr__(self):
        return f"<DataAsset {self.slug} [{self.asset_type}]>"


class LicenseInquiry(Base):
    """Lightweight interest tracking for data asset licensing."""

    __tablename__ = "license_inquiries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    asset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("data_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requester_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    message = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="pending")
    # Statuses: pending, responded, declined

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    asset = relationship("DataAsset", back_populates="inquiries")
    requester = relationship("User", foreign_keys=[requester_id])

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'responded', 'declined')",
            name="ck_license_inquiries_status",
        ),
    )

    def __repr__(self):
        return f"<LicenseInquiry asset={self.asset_id} status={self.status}>"
