"""Add installation and tool adapter columns to open_source_apps.

Revision ID: 050
Revises: 049
Create Date: 2026-03-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers
revision = '050'
down_revision = '049'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('open_source_apps', sa.Column('install_commands', JSONB, nullable=True))
    op.add_column('open_source_apps', sa.Column('verification_command', sa.String(), nullable=True))
    op.add_column('open_source_apps', sa.Column('adapter_type', sa.String(), nullable=True))
    op.add_column('open_source_apps', sa.Column('default_port', sa.Integer(), nullable=True))
    op.add_column('open_source_apps', sa.Column('health_check_url', sa.String(), nullable=True))
    op.add_column('open_source_apps', sa.Column('api_base_path', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('open_source_apps', 'api_base_path')
    op.drop_column('open_source_apps', 'health_check_url')
    op.drop_column('open_source_apps', 'default_port')
    op.drop_column('open_source_apps', 'adapter_type')
    op.drop_column('open_source_apps', 'verification_command')
    op.drop_column('open_source_apps', 'install_commands')
