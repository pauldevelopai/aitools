"""Add legal_framework_docs and legal_framework_versions tables

Revision ID: 027
Revises: 026
Create Date: 2026-02-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '027'
down_revision = '026'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: legal_framework_docs — per-user framework identity
    op.create_table(
        'legal_framework_docs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('organization_profile_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('organization_profiles.id', ondelete='SET NULL'),
                  nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        # current_version_id added via ALTER after versions table exists
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Step 2: legal_framework_versions — immutable version snapshots
    op.create_table(
        'legal_framework_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('framework_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('legal_framework_docs.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, default='draft', index=True),
        # User selections
        sa.Column('framework_config', postgresql.JSONB(), nullable=True),
        # Narrative summary
        sa.Column('narrative_markdown', sa.Text(), nullable=True),
        # Checklist items
        sa.Column('checklist_items', postgresql.JSONB(), nullable=True),
        sa.Column('change_notes', sa.Text(), nullable=True),
        # Publishing
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('published_by', postgresql.UUID(as_uuid=True),
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
            name='ck_legal_framework_versions_status',
        ),
        sa.UniqueConstraint(
            'framework_id', 'version_number',
            name='uq_legal_framework_versions_framework_version',
        ),
    )
    op.create_index(
        'ix_legal_framework_versions_framework_status',
        'legal_framework_versions',
        ['framework_id', 'status'],
    )

    # Step 3: Add current_version_id FK to legal_framework_docs
    op.add_column(
        'legal_framework_docs',
        sa.Column('current_version_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_legal_framework_docs_current_version',
        'legal_framework_docs',
        'legal_framework_versions',
        ['current_version_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_legal_framework_docs_current_version', 'legal_framework_docs', type_='foreignkey')
    op.drop_column('legal_framework_docs', 'current_version_id')
    op.drop_index('ix_legal_framework_versions_framework_status', table_name='legal_framework_versions')
    op.drop_table('legal_framework_versions')
    op.drop_table('legal_framework_docs')
