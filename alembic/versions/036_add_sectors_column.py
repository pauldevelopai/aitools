"""Add sectors JSONB column to discovered_tools, use_cases, discovered_resources, content_items.

Revision ID: 036
Revises: 035
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "036"
down_revision = "035"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("discovered_tools", sa.Column("sectors", postgresql.JSONB(), nullable=True))
    op.add_column("use_cases", sa.Column("sectors", postgresql.JSONB(), nullable=True))
    op.add_column("discovered_resources", sa.Column("sectors", postgresql.JSONB(), nullable=True))
    op.add_column("content_items", sa.Column("sectors", postgresql.JSONB(), nullable=True))


def downgrade():
    op.drop_column("content_items", "sectors")
    op.drop_column("discovered_resources", "sectors")
    op.drop_column("use_cases", "sectors")
    op.drop_column("discovered_tools", "sectors")
