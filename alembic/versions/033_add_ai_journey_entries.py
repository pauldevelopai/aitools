"""Add AI journey entries table and stage column on media_organizations.

Revision ID: 033
Revises: 032
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


def upgrade():
    # Create ai_journey_entries table
    op.create_table(
        "ai_journey_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("media_organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("stage", sa.String(30), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("recorded_by_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Add ai_journey_stage column to media_organizations
    op.add_column(
        "media_organizations",
        sa.Column("ai_journey_stage", sa.String(30), server_default="not_started", nullable=True),
    )


def downgrade():
    op.drop_column("media_organizations", "ai_journey_stage")
    op.drop_table("ai_journey_entries")
