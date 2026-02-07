"""Add ethics_policies and ethics_policy_versions tables

Revision ID: 026
Revises: 025
Create Date: 2026-02-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '026'
down_revision = '025'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: ethics_policies — per-user policy identity
    op.create_table(
        'ethics_policies',
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

    # Step 2: ethics_policy_versions — immutable version snapshots
    op.create_table(
        'ethics_policy_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('policy_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('ethics_policies.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, default='draft', index=True),
        # Structured section data
        sa.Column('sections_data', postgresql.JSONB(), nullable=True),
        sa.Column('content_markdown', sa.Text(), nullable=True),
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
            name='ck_ethics_policy_versions_status',
        ),
        sa.UniqueConstraint(
            'policy_id', 'version_number',
            name='uq_ethics_policy_versions_policy_version',
        ),
    )
    op.create_index(
        'ix_ethics_policy_versions_policy_status',
        'ethics_policy_versions',
        ['policy_id', 'status'],
    )

    # Step 3: Add current_version_id FK to ethics_policies
    op.add_column(
        'ethics_policies',
        sa.Column('current_version_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_ethics_policies_current_version',
        'ethics_policies',
        'ethics_policy_versions',
        ['current_version_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_ethics_policies_current_version', 'ethics_policies', type_='foreignkey')
    op.drop_column('ethics_policies', 'current_version_id')
    op.drop_index('ix_ethics_policy_versions_policy_status', table_name='ethics_policy_versions')
    op.drop_table('ethics_policy_versions')
    op.drop_table('ethics_policies')
