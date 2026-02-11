"""Add row_overrides column to spreadsheet_imports.

Revision ID: 032
Revises: 031
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "spreadsheet_imports",
        sa.Column("row_overrides", JSONB, server_default="{}", nullable=True),
    )


def downgrade():
    op.drop_column("spreadsheet_imports", "row_overrides")
