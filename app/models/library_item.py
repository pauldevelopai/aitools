"""Public Library Item model — admin-curated reference documents.

Single-table model (no versioning needed — admin edits directly).
Stores real-world policy and regulation documents for user reference.
Supports automated ingestion with dedup via content_hash and source_id.
"""
import hashlib
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, DateTime, Text, Boolean, Date,
    CheckConstraint, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
import re

from app.db import Base
from app.models.legal_builder import JURISDICTIONS, JURISDICTION_KEYS


# =============================================================================
# CONSTANTS
# =============================================================================

DOCUMENT_TYPES = [
    {"key": "regulation", "label": "Regulation"},
    {"key": "policy", "label": "Policy"},
    {"key": "guidance", "label": "Guidance"},
    {"key": "standard", "label": "Standard"},
    {"key": "framework", "label": "Framework"},
]

DOCUMENT_TYPE_KEYS = [d["key"] for d in DOCUMENT_TYPES]
DOCUMENT_TYPE_MAP = {d["key"]: d for d in DOCUMENT_TYPES}


class LibraryItem(Base):
    """A curated reference document in the public library."""

    __tablename__ = "library_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True, index=True)

    document_type = Column(String, nullable=False, index=True)
    jurisdiction = Column(String, nullable=True, index=True)

    tags = Column(JSONB, nullable=True)

    publisher = Column(String, nullable=True)
    publication_date = Column(Date, nullable=True)
    source_url = Column(String, nullable=True)

    summary = Column(Text, nullable=True)
    content_markdown = Column(Text, nullable=False)
    sections = Column(JSONB, nullable=True)

    is_published = Column(Boolean, default=False, nullable=False, index=True)

    # Ingestion tracking — for dedup and re-ingest
    source_id = Column(String, nullable=True, unique=True, index=True)
    content_hash = Column(String(64), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "document_type IN ('regulation', 'policy', 'guidance', 'standard', 'framework')",
            name="ck_library_items_document_type",
        ),
        Index("ix_library_items_type_jurisdiction", "document_type", "jurisdiction"),
    )

    def __repr__(self):
        return f"<LibraryItem {self.slug} type={self.document_type}>"

    @staticmethod
    def generate_slug(title: str) -> str:
        """Generate a URL-safe slug from a title."""
        slug = title.lower()
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        slug = re.sub(r"[\s_]+", "-", slug)
        return slug.strip("-")[:100]

    @staticmethod
    def compute_hash(content: str) -> str:
        """SHA-256 hash of content for change detection."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
