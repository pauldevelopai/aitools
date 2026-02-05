"""Governance & Tools Intelligence models for testing tools and tracking frameworks."""
from sqlalchemy import (
    Column, String, DateTime, Text, ForeignKey, Boolean, Integer, Float,
    CheckConstraint, Index, Date
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db import Base


class ToolsCatalogEntry(Base):
    """Extension table for tools in the catalog - links to approved DiscoveredTools.

    Provides additional testing and governance metadata for tools.
    """
    __tablename__ = "tools_catalog"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Link to discovered tool (optional - can be standalone for manually added tools)
    discovered_tool_id = Column(
        UUID(as_uuid=True),
        ForeignKey("discovered_tools.id", ondelete="CASCADE"),
        nullable=True,
        unique=True,
        index=True
    )

    # Tool identification (for standalone entries)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True, index=True)
    url = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    # Testing configuration
    test_frequency = Column(String, default="weekly")  # daily, weekly, monthly, manual
    is_testable = Column(Boolean, default=True)
    test_config = Column(JSONB, nullable=True, default=dict)  # API keys, endpoints, etc.

    # Governance metadata
    requires_api_key = Column(Boolean, default=False)
    data_processing_type = Column(String, nullable=True)  # local, cloud, hybrid
    data_retention_policy = Column(Text, nullable=True)
    privacy_policy_url = Column(String, nullable=True)
    terms_of_service_url = Column(String, nullable=True)
    gdpr_compliant = Column(Boolean, nullable=True)

    # Applicable frameworks (JSONB list of framework slugs)
    applicable_frameworks = Column(JSONB, nullable=True, default=list)

    # Testing status
    last_tested_at = Column(DateTime(timezone=True), nullable=True)
    last_test_passed = Column(Boolean, nullable=True)
    test_score = Column(Float, nullable=True)  # 0.0-1.0
    red_flags = Column(JSONB, nullable=True, default=list)  # List of issues found

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    discovered_tool = relationship("DiscoveredTool", backref="catalog_entry")
    test_cases = relationship("ToolTestCase", back_populates="tool", cascade="all, delete-orphan")
    tests = relationship("ToolTest", back_populates="tool", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "test_frequency IN ('daily', 'weekly', 'monthly', 'manual')",
            name='ck_tools_catalog_test_frequency'
        ),
    )

    def __repr__(self):
        return f"<ToolsCatalogEntry {self.name}>"


class ToolTestCase(Base):
    """Reusable test case definitions for tools."""
    __tablename__ = "tool_test_cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Link to tool (optional - can be generic test cases)
    tool_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tools_catalog.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Test identification
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    test_type = Column(String, nullable=False)  # availability, functionality, performance, security, privacy

    # Test configuration
    test_steps = Column(JSONB, nullable=False, default=list)  # List of step definitions
    expected_outcome = Column(Text, nullable=True)
    timeout_seconds = Column(Integer, default=30)

    # Categorization
    category = Column(String, nullable=True)  # api, web, cli, integration
    severity = Column(String, default="medium")  # critical, high, medium, low

    # Automation
    is_automated = Column(Boolean, default=False)
    automation_script = Column(Text, nullable=True)  # Python code or reference

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    tool = relationship("ToolsCatalogEntry", back_populates="test_cases")
    tests = relationship("ToolTest", back_populates="test_case", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "test_type IN ('availability', 'functionality', 'performance', 'security', 'privacy')",
            name='ck_tool_test_cases_test_type'
        ),
        CheckConstraint(
            "severity IN ('critical', 'high', 'medium', 'low')",
            name='ck_tool_test_cases_severity'
        ),
    )

    def __repr__(self):
        return f"<ToolTestCase {self.name}>"


class ToolTest(Base):
    """Individual test run results."""
    __tablename__ = "tool_tests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Links
    tool_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tools_catalog.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    test_case_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tool_test_cases.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Execution
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # Results
    passed = Column(Boolean, nullable=True)
    score = Column(Float, nullable=True)  # 0.0-1.0
    status = Column(String, nullable=False, default="running")  # running, passed, failed, error, skipped

    # Detailed results
    metrics = Column(JSONB, nullable=True, default=dict)  # Response time, memory, etc.
    output = Column(Text, nullable=True)  # Test output/logs
    error_message = Column(Text, nullable=True)
    red_flags = Column(JSONB, nullable=True, default=list)  # Issues found

    # Context
    test_environment = Column(String, nullable=True)  # production, staging, local
    triggered_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    workflow_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    tool = relationship("ToolsCatalogEntry", back_populates="tests")
    test_case = relationship("ToolTestCase", back_populates="tests")
    triggerer = relationship("User", foreign_keys=[triggered_by])
    workflow_run = relationship("WorkflowRun")

    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'passed', 'failed', 'error', 'skipped')",
            name='ck_tool_tests_status'
        ),
        Index('ix_tool_tests_tool_started', 'tool_id', 'started_at'),
    )

    def __repr__(self):
        return f"<ToolTest {self.id} tool={self.tool_id} status={self.status}>"


class GovernanceFramework(Base):
    """Legal and regulatory frameworks (GDPR, EU AI Act, etc.)."""
    __tablename__ = "governance_frameworks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Identification
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True, index=True)
    short_name = Column(String, nullable=True)  # e.g., "GDPR", "EU AI Act"

    # Classification
    framework_type = Column(String, nullable=False)  # regulation, directive, guidance, standard, policy
    jurisdiction = Column(String, nullable=False, index=True)  # EU, US, UK, Global, etc.
    jurisdiction_scope = Column(String, nullable=True)  # federal, state, regional, international

    # Content
    description = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)  # AI-generated summary
    key_provisions = Column(JSONB, nullable=True, default=list)  # List of main points

    # Dates
    effective_date = Column(Date, nullable=True)
    last_amended_date = Column(Date, nullable=True)
    version = Column(String, nullable=True)

    # Sources
    official_url = Column(String, nullable=True)
    source_documents = Column(JSONB, nullable=True, default=list)  # List of source URLs

    # Applicability
    applies_to = Column(JSONB, nullable=True, default=list)  # ["ai_systems", "data_processing", "journalism"]
    scope_description = Column(Text, nullable=True)

    # Evidence
    evidence_sources = Column(JSONB, nullable=True, default=list)  # [{url, retrieved_at, excerpt}]

    # Status
    status = Column(String, default="draft")  # draft, active, superseded, archived

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    controls = relationship("GovernanceControl", back_populates="framework", cascade="all, delete-orphan")
    content_items = relationship("ContentItem", back_populates="framework")

    __table_args__ = (
        CheckConstraint(
            "framework_type IN ('regulation', 'directive', 'guidance', 'standard', 'policy', 'treaty')",
            name='ck_governance_frameworks_type'
        ),
        CheckConstraint(
            "status IN ('draft', 'active', 'superseded', 'archived')",
            name='ck_governance_frameworks_status'
        ),
    )

    def __repr__(self):
        return f"<GovernanceFramework {self.short_name or self.name}>"


class GovernanceControl(Base):
    """Specific controls/obligations within a governance framework."""
    __tablename__ = "governance_controls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Link to framework
    framework_id = Column(
        UUID(as_uuid=True),
        ForeignKey("governance_frameworks.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Identification
    control_id = Column(String, nullable=True)  # e.g., "Article 5", "Section 2.3"
    name = Column(String, nullable=False)

    # Content
    description = Column(Text, nullable=True)
    obligations = Column(JSONB, nullable=True, default=list)  # List of specific requirements

    # Classification
    control_type = Column(String, nullable=True)  # transparency, accountability, security, rights, etc.
    risk_level = Column(String, nullable=True)  # high, medium, low

    # Applicability
    applies_to_tools = Column(Boolean, default=False)
    applies_to_data = Column(Boolean, default=False)
    applies_to_content = Column(Boolean, default=False)
    applicability_notes = Column(Text, nullable=True)

    # Implementation guidance
    implementation_guidance = Column(Text, nullable=True)
    examples = Column(JSONB, nullable=True, default=list)

    # Compliance
    compliance_indicators = Column(JSONB, nullable=True, default=list)

    # Evidence
    evidence_sources = Column(JSONB, nullable=True, default=list)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    framework = relationship("GovernanceFramework", back_populates="controls")

    def __repr__(self):
        return f"<GovernanceControl {self.control_id or self.name}>"


class ContentItem(Base):
    """Draft/review/published content for Grounded pages."""
    __tablename__ = "content_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Identification
    title = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True, index=True)

    # Content
    content_markdown = Column(Text, nullable=False)  # Main content in markdown
    summary = Column(Text, nullable=True)
    excerpt = Column(Text, nullable=True)  # Short preview text

    # Classification
    content_type = Column(String, nullable=False)  # guide, framework_summary, tool_guide, policy, faq
    section = Column(String, nullable=False, index=True)  # foundations, resources, governance, tools

    # Categorization
    tags = Column(JSONB, nullable=True, default=list)
    jurisdiction = Column(String, nullable=True, index=True)  # For governance content
    audience = Column(JSONB, nullable=True, default=list)  # ["journalists", "editors", "technologists"]

    # Related entities
    framework_id = Column(
        UUID(as_uuid=True),
        ForeignKey("governance_frameworks.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    tool_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tools_catalog.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Evidence/Sources
    sources = Column(JSONB, nullable=True, default=list)  # [{url, title, retrieved_at, excerpt}]

    # Workflow
    status = Column(String, default="draft", index=True)  # draft, pending_review, approved, published, archived

    # Review
    reviewed_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)

    # Publishing
    published_at = Column(DateTime(timezone=True), nullable=True)
    published_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Generation metadata
    generated_by_workflow = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_runs.id", ondelete="SET NULL"),
        nullable=True
    )
    generation_config = Column(JSONB, nullable=True, default=dict)

    # Versioning
    version = Column(Integer, default=1)
    parent_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("content_items.id", ondelete="SET NULL"),
        nullable=True
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    framework = relationship("GovernanceFramework", back_populates="content_items")
    tool = relationship("ToolsCatalogEntry")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    publisher = relationship("User", foreign_keys=[published_by])
    workflow_run = relationship("WorkflowRun")
    parent_version = relationship("ContentItem", remote_side=[id])

    __table_args__ = (
        CheckConstraint(
            "content_type IN ('guide', 'framework_summary', 'tool_guide', 'policy', 'faq', 'checklist', 'template')",
            name='ck_content_items_content_type'
        ),
        CheckConstraint(
            "section IN ('foundations', 'resources', 'governance', 'tools', 'use-cases')",
            name='ck_content_items_section'
        ),
        CheckConstraint(
            "status IN ('draft', 'pending_review', 'approved', 'published', 'archived')",
            name='ck_content_items_status'
        ),
    )

    def __repr__(self):
        return f"<ContentItem {self.slug} status={self.status}>"


class GovernanceTarget(Base):
    """Queue of items to be processed by the Governance workflow."""
    __tablename__ = "governance_targets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Target identification
    target_type = Column(String, nullable=False)  # framework, tool, template
    target_name = Column(String, nullable=False)
    target_description = Column(Text, nullable=True)

    # For framework targets
    jurisdiction = Column(String, nullable=True)

    # For tool targets
    tool_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tools_catalog.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Research hints
    search_terms = Column(JSONB, nullable=True, default=list)  # Keywords to search
    known_urls = Column(JSONB, nullable=True, default=list)  # URLs to fetch

    # Processing
    status = Column(String, default="queued", index=True)  # queued, processing, completed, failed, cancelled
    priority = Column(Integer, default=5)  # 1-10, lower is higher priority

    # Workflow tracking
    workflow_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Results
    output_content_ids = Column(JSONB, nullable=True, default=list)  # List of generated ContentItem IDs
    output_framework_id = Column(
        UUID(as_uuid=True),
        ForeignKey("governance_frameworks.id", ondelete="SET NULL"),
        nullable=True
    )
    processing_notes = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    # Queue management
    queued_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # User tracking
    queued_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    tool = relationship("ToolsCatalogEntry")
    workflow_run = relationship("WorkflowRun")
    output_framework = relationship("GovernanceFramework")
    queuer = relationship("User", foreign_keys=[queued_by])

    __table_args__ = (
        CheckConstraint(
            "target_type IN ('framework', 'tool', 'template')",
            name='ck_governance_targets_target_type'
        ),
        CheckConstraint(
            "status IN ('queued', 'processing', 'completed', 'failed', 'cancelled')",
            name='ck_governance_targets_status'
        ),
        Index('ix_governance_targets_queue', 'status', 'priority', 'queued_at'),
    )

    def __repr__(self):
        return f"<GovernanceTarget {self.target_type}:{self.target_name} status={self.status}>"
