"""Create user_tool_installations table.

Revision ID: 051
Revises: 050
Create Date: 2026-03-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers
revision = '051'
down_revision = '050'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'user_tool_installations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('app_id', UUID(as_uuid=True), sa.ForeignKey('open_source_apps.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='not_installed'),
        sa.Column('installed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_healthy', sa.Boolean(), nullable=True),
        sa.Column('last_health_check', sa.DateTime(timezone=True), nullable=True),
        sa.Column('user_rating', sa.Integer(), nullable=True),
        sa.Column('user_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('user_id', 'app_id', name='uq_user_tool_installations_user_app'),
    )
    op.create_index('ix_user_tool_installations_user_id', 'user_tool_installations', ['user_id'])
    op.create_index('ix_user_tool_installations_app_id', 'user_tool_installations', ['app_id'])


def downgrade() -> None:
    op.drop_index('ix_user_tool_installations_app_id')
    op.drop_index('ix_user_tool_installations_user_id')
    op.drop_table('user_tool_installations')
