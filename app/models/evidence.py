"""Evidence models for tracking sources of factual claims."""
from sqlalchemy import Column, String, DateTime, Text, Float, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.db import Base


class EvidenceSource(Base):
    """Tracks evidence sources for factual claims about organizations/journalists.

    Each piece of enrichment data should link back to one or more evidence sources,
    providing an audit trail and enabling fact verification.
    """

    __tablename__ = "evidence_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # What entity this evidence relates to
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("media_organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    journalist_id = Column(
        UUID(as_uuid=True),
        ForeignKey("journalists.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Source information
    source_url = Column(String(2000), nullable=False)
    source_type = Column(String(50), nullable=False)  # webpage, api, document, manual
    page_title = Column(String(500), nullable=True)

    # Content snapshot
    content_text = Column(Text, nullable=True)  # Plain text extract
    content_html = Column(Text, nullable=True)  # Original HTML (optional)
    content_hash = Column(String(64), nullable=True)  # SHA256 for dedup

    # What was extracted
    field_name = Column(String(100), nullable=False)  # e.g., "description", "focus_areas", "key_people"
    extracted_value = Column(Text, nullable=True)  # The actual extracted value
    confidence_score = Column(Float, nullable=True)  # 0.0-1.0

    # Extraction metadata
    extraction_method = Column(String(50), nullable=True)  # llm, regex, xpath, manual
    extraction_prompt = Column(Text, nullable=True)  # LLM prompt used if applicable
    extraction_model = Column(String(100), nullable=True)  # e.g., "gpt-4o-mini"

    # Workflow tracking
    workflow_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Timestamps
    retrieved_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    organization = relationship("MediaOrganization", backref="evidence_sources")
    journalist = relationship("Journalist", backref="evidence_sources")
    workflow_run = relationship("WorkflowRun", backref="evidence_sources")

    __table_args__ = (
        CheckConstraint(
            "source_type IN ('webpage', 'api', 'document', 'manual')",
            name='ck_evidence_source_type'
        ),
        CheckConstraint(
            'confidence_score IS NULL OR (confidence_score >= 0.0 AND confidence_score <= 1.0)',
            name='ck_evidence_confidence_range'
        ),
        # At least one entity must be specified
        CheckConstraint(
            'organization_id IS NOT NULL OR journalist_id IS NOT NULL',
            name='ck_evidence_entity_required'
        ),
    )

    def __repr__(self):
        return f"<EvidenceSource {self.id} field={self.field_name} confidence={self.confidence_score}>"


class WebPageSnapshot(Base):
    """Stores fetched web page content for evidence and auditing.

    This provides the raw artifact storage for pages fetched during enrichment.
    """

    __tablename__ = "webpage_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # URL and identification
    url = Column(String(2000), nullable=False, index=True)
    url_hash = Column(String(64), nullable=False, index=True)  # SHA256 of URL for fast lookup
    page_type = Column(String(50), nullable=True)  # homepage, about, team, contact, news, etc.

    # Content
    html_content = Column(Text, nullable=True)
    text_content = Column(Text, nullable=True)
    title = Column(String(500), nullable=True)

    # Metadata
    status_code = Column(String(10), nullable=True)
    content_type = Column(String(100), nullable=True)
    content_length = Column(String(20), nullable=True)
    headers = Column(JSONB, nullable=True, default=dict)

    # Extraction results (structured data pulled from this page)
    extracted_data = Column(JSONB, nullable=True, default=dict)

    # Workflow tracking
    workflow_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("media_organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Timestamps
    fetched_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    workflow_run = relationship("WorkflowRun", backref="webpage_snapshots")
    organization = relationship("MediaOrganization", backref="webpage_snapshots")

    def __repr__(self):
        return f"<WebPageSnapshot {self.id} url={self.url[:50]}...>"
