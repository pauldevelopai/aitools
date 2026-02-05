"""Add evidence_sources and webpage_snapshots tables for Partner Intelligence

Revision ID: 020
Revises: 019
Create Date: 2025-02-04

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '020'
down_revision = '019'
branch_labels = None
depends_on = None


def upgrade():
    # Create evidence_sources table
    op.create_table(
        'evidence_sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),

        # Entity references
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('journalist_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Source information
        sa.Column('source_url', sa.String(2000), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('page_title', sa.String(500), nullable=True),

        # Content snapshot
        sa.Column('content_text', sa.Text(), nullable=True),
        sa.Column('content_html', sa.Text(), nullable=True),
        sa.Column('content_hash', sa.String(64), nullable=True),

        # Extraction data
        sa.Column('field_name', sa.String(100), nullable=False),
        sa.Column('extracted_value', sa.Text(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),

        # Extraction metadata
        sa.Column('extraction_method', sa.String(50), nullable=True),
        sa.Column('extraction_prompt', sa.Text(), nullable=True),
        sa.Column('extraction_model', sa.String(100), nullable=True),

        # Workflow tracking
        sa.Column('workflow_run_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Timestamps
        sa.Column('retrieved_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['organization_id'], ['media_organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['journalist_id'], ['journalists.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workflow_run_id'], ['workflow_runs.id'], ondelete='SET NULL'),
        sa.CheckConstraint(
            "source_type IN ('webpage', 'api', 'document', 'manual')",
            name='ck_evidence_source_type'
        ),
        sa.CheckConstraint(
            'confidence_score IS NULL OR (confidence_score >= 0.0 AND confidence_score <= 1.0)',
            name='ck_evidence_confidence_range'
        ),
        sa.CheckConstraint(
            'organization_id IS NOT NULL OR journalist_id IS NOT NULL',
            name='ck_evidence_entity_required'
        ),
    )

    # Create indexes for evidence_sources
    op.create_index('ix_evidence_sources_organization_id', 'evidence_sources', ['organization_id'])
    op.create_index('ix_evidence_sources_journalist_id', 'evidence_sources', ['journalist_id'])
    op.create_index('ix_evidence_sources_workflow_run_id', 'evidence_sources', ['workflow_run_id'])
    op.create_index('ix_evidence_sources_field_name', 'evidence_sources', ['field_name'])

    # Create webpage_snapshots table
    op.create_table(
        'webpage_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),

        # URL and identification
        sa.Column('url', sa.String(2000), nullable=False),
        sa.Column('url_hash', sa.String(64), nullable=False),
        sa.Column('page_type', sa.String(50), nullable=True),

        # Content
        sa.Column('html_content', sa.Text(), nullable=True),
        sa.Column('text_content', sa.Text(), nullable=True),
        sa.Column('title', sa.String(500), nullable=True),

        # Metadata
        sa.Column('status_code', sa.String(10), nullable=True),
        sa.Column('content_type', sa.String(100), nullable=True),
        sa.Column('content_length', sa.String(20), nullable=True),
        sa.Column('headers', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),

        # Extraction results
        sa.Column('extracted_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),

        # Workflow tracking
        sa.Column('workflow_run_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Timestamps
        sa.Column('fetched_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['workflow_run_id'], ['workflow_runs.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_id'], ['media_organizations.id'], ondelete='CASCADE'),
    )

    # Create indexes for webpage_snapshots
    op.create_index('ix_webpage_snapshots_url', 'webpage_snapshots', ['url'])
    op.create_index('ix_webpage_snapshots_url_hash', 'webpage_snapshots', ['url_hash'])
    op.create_index('ix_webpage_snapshots_workflow_run_id', 'webpage_snapshots', ['workflow_run_id'])
    op.create_index('ix_webpage_snapshots_organization_id', 'webpage_snapshots', ['organization_id'])


def downgrade():
    # Drop webpage_snapshots indexes and table
    op.drop_index('ix_webpage_snapshots_organization_id', table_name='webpage_snapshots')
    op.drop_index('ix_webpage_snapshots_workflow_run_id', table_name='webpage_snapshots')
    op.drop_index('ix_webpage_snapshots_url_hash', table_name='webpage_snapshots')
    op.drop_index('ix_webpage_snapshots_url', table_name='webpage_snapshots')
    op.drop_table('webpage_snapshots')

    # Drop evidence_sources indexes and table
    op.drop_index('ix_evidence_sources_field_name', table_name='evidence_sources')
    op.drop_index('ix_evidence_sources_workflow_run_id', table_name='evidence_sources')
    op.drop_index('ix_evidence_sources_journalist_id', table_name='evidence_sources')
    op.drop_index('ix_evidence_sources_organization_id', table_name='evidence_sources')
    op.drop_table('evidence_sources')
