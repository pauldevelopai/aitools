"""Add governance and tools intelligence tables

Revision ID: 022
Revises: 021
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '022'
down_revision = '021'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tools Catalog - extends discovered tools with testing/governance metadata
    op.create_table(
        'tools_catalog',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('discovered_tool_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('discovered_tools.id', ondelete='CASCADE'),
                  nullable=True, unique=True, index=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('url', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        # Testing configuration
        sa.Column('test_frequency', sa.String(), default='weekly'),
        sa.Column('is_testable', sa.Boolean(), default=True),
        sa.Column('test_config', postgresql.JSONB(), nullable=True, default=dict),
        # Governance metadata
        sa.Column('requires_api_key', sa.Boolean(), default=False),
        sa.Column('data_processing_type', sa.String(), nullable=True),
        sa.Column('data_retention_policy', sa.Text(), nullable=True),
        sa.Column('privacy_policy_url', sa.String(), nullable=True),
        sa.Column('terms_of_service_url', sa.String(), nullable=True),
        sa.Column('gdpr_compliant', sa.Boolean(), nullable=True),
        sa.Column('applicable_frameworks', postgresql.JSONB(), nullable=True, default=list),
        # Testing status
        sa.Column('last_tested_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_test_passed', sa.Boolean(), nullable=True),
        sa.Column('test_score', sa.Float(), nullable=True),
        sa.Column('red_flags', postgresql.JSONB(), nullable=True, default=list),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        # Constraint
        sa.CheckConstraint("test_frequency IN ('daily', 'weekly', 'monthly', 'manual')", name='ck_tools_catalog_test_frequency'),
    )

    # Tool Test Cases - reusable test definitions
    op.create_table(
        'tool_test_cases',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tool_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tools_catalog.id', ondelete='CASCADE'),
                  nullable=True, index=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('test_type', sa.String(), nullable=False),
        sa.Column('test_steps', postgresql.JSONB(), nullable=False, default=list),
        sa.Column('expected_outcome', sa.Text(), nullable=True),
        sa.Column('timeout_seconds', sa.Integer(), default=30),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('severity', sa.String(), default='medium'),
        sa.Column('is_automated', sa.Boolean(), default=False),
        sa.Column('automation_script', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.CheckConstraint("test_type IN ('availability', 'functionality', 'performance', 'security', 'privacy')", name='ck_tool_test_cases_test_type'),
        sa.CheckConstraint("severity IN ('critical', 'high', 'medium', 'low')", name='ck_tool_test_cases_severity'),
    )

    # Tool Tests - individual test run results
    op.create_table(
        'tool_tests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tool_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tools_catalog.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('test_case_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tool_test_cases.id', ondelete='SET NULL'),
                  nullable=True, index=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('passed', sa.Boolean(), nullable=True),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, default='running'),
        sa.Column('metrics', postgresql.JSONB(), nullable=True, default=dict),
        sa.Column('output', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('red_flags', postgresql.JSONB(), nullable=True, default=list),
        sa.Column('test_environment', sa.String(), nullable=True),
        sa.Column('triggered_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('workflow_run_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('workflow_runs.id', ondelete='SET NULL'),
                  nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('running', 'passed', 'failed', 'error', 'skipped')", name='ck_tool_tests_status'),
    )
    op.create_index('ix_tool_tests_tool_started', 'tool_tests', ['tool_id', 'started_at'])

    # Governance Frameworks - legal/regulatory frameworks
    op.create_table(
        'governance_frameworks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('short_name', sa.String(), nullable=True),
        sa.Column('framework_type', sa.String(), nullable=False),
        sa.Column('jurisdiction', sa.String(), nullable=False, index=True),
        sa.Column('jurisdiction_scope', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('key_provisions', postgresql.JSONB(), nullable=True, default=list),
        sa.Column('effective_date', sa.Date(), nullable=True),
        sa.Column('last_amended_date', sa.Date(), nullable=True),
        sa.Column('version', sa.String(), nullable=True),
        sa.Column('official_url', sa.String(), nullable=True),
        sa.Column('source_documents', postgresql.JSONB(), nullable=True, default=list),
        sa.Column('applies_to', postgresql.JSONB(), nullable=True, default=list),
        sa.Column('scope_description', sa.Text(), nullable=True),
        sa.Column('evidence_sources', postgresql.JSONB(), nullable=True, default=list),
        sa.Column('status', sa.String(), default='draft'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.CheckConstraint("framework_type IN ('regulation', 'directive', 'guidance', 'standard', 'policy', 'treaty')", name='ck_governance_frameworks_type'),
        sa.CheckConstraint("status IN ('draft', 'active', 'superseded', 'archived')", name='ck_governance_frameworks_status'),
    )

    # Governance Controls - specific obligations within frameworks
    op.create_table(
        'governance_controls',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('framework_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('governance_frameworks.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('control_id', sa.String(), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('obligations', postgresql.JSONB(), nullable=True, default=list),
        sa.Column('control_type', sa.String(), nullable=True),
        sa.Column('risk_level', sa.String(), nullable=True),
        sa.Column('applies_to_tools', sa.Boolean(), default=False),
        sa.Column('applies_to_data', sa.Boolean(), default=False),
        sa.Column('applies_to_content', sa.Boolean(), default=False),
        sa.Column('applicability_notes', sa.Text(), nullable=True),
        sa.Column('implementation_guidance', sa.Text(), nullable=True),
        sa.Column('examples', postgresql.JSONB(), nullable=True, default=list),
        sa.Column('compliance_indicators', postgresql.JSONB(), nullable=True, default=list),
        sa.Column('evidence_sources', postgresql.JSONB(), nullable=True, default=list),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Content Items - draft/review/published content
    op.create_table(
        'content_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('content_markdown', sa.Text(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('excerpt', sa.Text(), nullable=True),
        sa.Column('content_type', sa.String(), nullable=False),
        sa.Column('section', sa.String(), nullable=False, index=True),
        sa.Column('tags', postgresql.JSONB(), nullable=True, default=list),
        sa.Column('jurisdiction', sa.String(), nullable=True, index=True),
        sa.Column('audience', postgresql.JSONB(), nullable=True, default=list),
        sa.Column('framework_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('governance_frameworks.id', ondelete='SET NULL'),
                  nullable=True, index=True),
        sa.Column('tool_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tools_catalog.id', ondelete='SET NULL'),
                  nullable=True, index=True),
        sa.Column('sources', postgresql.JSONB(), nullable=True, default=list),
        sa.Column('status', sa.String(), default='draft', index=True),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('published_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('generated_by_workflow', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('workflow_runs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('generation_config', postgresql.JSONB(), nullable=True, default=dict),
        sa.Column('version', sa.Integer(), default=1),
        sa.Column('parent_version_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('content_items.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.CheckConstraint("content_type IN ('guide', 'framework_summary', 'tool_guide', 'policy', 'faq', 'checklist', 'template')", name='ck_content_items_content_type'),
        sa.CheckConstraint("section IN ('foundations', 'resources', 'governance', 'tools', 'use-cases')", name='ck_content_items_section'),
        sa.CheckConstraint("status IN ('draft', 'pending_review', 'approved', 'published', 'archived')", name='ck_content_items_status'),
    )

    # Governance Targets - queue of items to process
    op.create_table(
        'governance_targets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('target_type', sa.String(), nullable=False),
        sa.Column('target_name', sa.String(), nullable=False),
        sa.Column('target_description', sa.Text(), nullable=True),
        sa.Column('jurisdiction', sa.String(), nullable=True),
        sa.Column('tool_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tools_catalog.id', ondelete='SET NULL'),
                  nullable=True, index=True),
        sa.Column('search_terms', postgresql.JSONB(), nullable=True, default=list),
        sa.Column('known_urls', postgresql.JSONB(), nullable=True, default=list),
        sa.Column('status', sa.String(), default='queued', index=True),
        sa.Column('priority', sa.Integer(), default=5),
        sa.Column('workflow_run_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('workflow_runs.id', ondelete='SET NULL'),
                  nullable=True, index=True),
        sa.Column('output_content_ids', postgresql.JSONB(), nullable=True, default=list),
        sa.Column('output_framework_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('governance_frameworks.id', ondelete='SET NULL'), nullable=True),
        sa.Column('processing_notes', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('queued_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('queued_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.CheckConstraint("target_type IN ('framework', 'tool', 'template')", name='ck_governance_targets_target_type'),
        sa.CheckConstraint("status IN ('queued', 'processing', 'completed', 'failed', 'cancelled')", name='ck_governance_targets_status'),
    )
    op.create_index('ix_governance_targets_queue', 'governance_targets', ['status', 'priority', 'queued_at'])


def downgrade() -> None:
    op.drop_index('ix_governance_targets_queue', table_name='governance_targets')
    op.drop_table('governance_targets')
    op.drop_table('content_items')
    op.drop_table('governance_controls')
    op.drop_table('governance_frameworks')
    op.drop_index('ix_tool_tests_tool_started', table_name='tool_tests')
    op.drop_table('tool_tests')
    op.drop_table('tool_test_cases')
    op.drop_table('tools_catalog')
