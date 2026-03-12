"""Add preferred_language column to users.

Revision ID: 041
Revises: 040
"""
import sqlalchemy as sa
from alembic import op

revision = "041"
down_revision = "040"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("preferred_language", sa.String(), nullable=True, server_default="en"))


def downgrade():
    op.drop_column("users", "preferred_language")
