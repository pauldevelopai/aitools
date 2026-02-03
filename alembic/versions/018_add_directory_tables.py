"""Add directory tables for journalist and media organization tracking.

Revision ID: 018_add_directory_tables
Revises: 017_add_user_learning_profiles
Create Date: 2025-02-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '018'
down_revision = '017'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Media Organizations
    op.create_table(
        'media_organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('org_type', sa.String(50), nullable=False),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('website', sa.String(500), nullable=True),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_media_organizations_name', 'media_organizations', ['name'])

    # 2. Departments
    op.create_table(
        'departments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['organization_id'], ['media_organizations.id'], ondelete='CASCADE'),
    )

    # 3. Teams
    op.create_table(
        'teams',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('department_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='CASCADE'),
    )

    # 4. Journalists
    op.create_table(
        'journalists',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('department_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('team_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('role', sa.String(100), nullable=True),
        sa.Column('beat', sa.String(255), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('photo_url', sa.String(500), nullable=True),
        sa.Column('twitter', sa.String(100), nullable=True),
        sa.Column('linkedin', sa.String(255), nullable=True),
        sa.Column('website', sa.String(500), nullable=True),
        sa.Column('ai_skill_level', sa.String(20), nullable=True, server_default='none'),
        sa.Column('areas_of_interest', postgresql.JSONB(), nullable=True, server_default='[]'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['organization_id'], ['media_organizations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('email', name='uq_journalists_email'),
    )
    op.create_index('ix_journalists_email', 'journalists', ['email'])

    # 5. Engagements
    op.create_table(
        'engagements',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('journalist_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('engagement_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('topics_covered', postgresql.JSONB(), nullable=True, server_default='[]'),
        sa.Column('materials_used', postgresql.JSONB(), nullable=True, server_default='[]'),
        sa.Column('outcomes', sa.Text(), nullable=True),
        sa.Column('follow_up_actions', sa.Text(), nullable=True),
        sa.Column('follow_up_date', sa.Date(), nullable=True),
        sa.Column('skill_before', sa.String(20), nullable=True),
        sa.Column('skill_after', sa.String(20), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['journalist_id'], ['journalists.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_engagements_journalist_id', 'engagements', ['journalist_id'])
    op.create_index('ix_engagements_date', 'engagements', ['date'])

    # 6. Journalist Notes
    op.create_table(
        'journalist_notes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('journalist_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('note_type', sa.String(50), nullable=True, server_default='general'),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_private', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['journalist_id'], ['journalists.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_journalist_notes_journalist_id', 'journalist_notes', ['journalist_id'])

    # 7. Engagement Documents
    op.create_table(
        'engagement_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('engagement_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('doc_type', sa.String(50), nullable=False),
        sa.Column('url', sa.String(500), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['engagement_id'], ['engagements.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_engagement_documents_engagement_id', 'engagement_documents', ['engagement_id'])


def downgrade() -> None:
    op.drop_index('ix_engagement_documents_engagement_id', table_name='engagement_documents')
    op.drop_table('engagement_documents')

    op.drop_index('ix_journalist_notes_journalist_id', table_name='journalist_notes')
    op.drop_table('journalist_notes')

    op.drop_index('ix_engagements_date', table_name='engagements')
    op.drop_index('ix_engagements_journalist_id', table_name='engagements')
    op.drop_table('engagements')

    op.drop_index('ix_journalists_email', table_name='journalists')
    op.drop_table('journalists')

    op.drop_table('teams')
    op.drop_table('departments')

    op.drop_index('ix_media_organizations_name', table_name='media_organizations')
    op.drop_table('media_organizations')
