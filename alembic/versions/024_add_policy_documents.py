"""Add policy_documents and policy_document_versions tables

Revision ID: 024
Revises: 023
Create Date: 2026-02-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '024'
down_revision = '023'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # policy_documents — document identity and ownership
    op.create_table(
        'policy_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('media_organizations.id', ondelete='CASCADE'),
                  nullable=True, index=True),
        sa.Column('doc_type', sa.String(), nullable=False, index=True),
        sa.Column('subtype', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('visibility', sa.String(), nullable=False, default='private'),
        # current_version_id added via ALTER after versions table exists
        sa.Column('created_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'),
                  nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "doc_type IN ('ethics_policy', 'legal_framework')",
            name='ck_policy_documents_doc_type',
        ),
        sa.CheckConstraint(
            "visibility IN ('private', 'shared', 'public')",
            name='ck_policy_documents_visibility',
        ),
    )

    # policy_document_versions — immutable version snapshots
    op.create_table(
        'policy_document_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('policy_documents.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, default='draft', index=True),
        # Content
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('content_markdown', sa.Text(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('change_notes', sa.Text(), nullable=True),
        # Attribution metadata
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('publisher', sa.String(), nullable=True),
        sa.Column('publication_date', sa.Date(), nullable=True),
        sa.Column('jurisdiction', sa.String(), nullable=True, index=True),
        sa.Column('source_url', sa.String(), nullable=True),
        sa.Column('license_notes', sa.Text(), nullable=True),
        # Publishing
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('published_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'),
                  nullable=True),
        # Provenance
        sa.Column('created_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'),
                  nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        # Constraints
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name='ck_policy_doc_versions_status',
        ),
        sa.UniqueConstraint(
            'document_id', 'version_number',
            name='uq_policy_doc_versions_doc_version',
        ),
    )
    op.create_index(
        'ix_policy_doc_versions_doc_status',
        'policy_document_versions',
        ['document_id', 'status'],
    )

    # Now add the current_version_id FK column to policy_documents
    op.add_column(
        'policy_documents',
        sa.Column('current_version_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_policy_documents_current_version',
        'policy_documents',
        'policy_document_versions',
        ['current_version_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_policy_documents_current_version', 'policy_documents', type_='foreignkey')
    op.drop_column('policy_documents', 'current_version_id')
    op.drop_index('ix_policy_doc_versions_doc_status', table_name='policy_document_versions')
    op.drop_table('policy_document_versions')
    op.drop_table('policy_documents')
