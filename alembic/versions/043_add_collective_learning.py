"""Add network_insights table for collective learning dashboard.

Revision ID: 043
Revises: 042
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "043"
down_revision = "042"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "network_insights",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("insight_type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("detail_data", postgresql.JSONB(), nullable=True, server_default="{}"),
        sa.Column("sector", sa.String(), nullable=True),
        sa.Column("region", sa.String(), nullable=True),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "insight_type IN ('tool_adoption', 'workflow_pattern', 'use_case_success', 'sector_trend', 'skill_growth')",
            name="ck_network_insights_type",
        ),
    )
    op.create_index("ix_network_insights_type", "network_insights", ["insight_type"])
    op.create_index("ix_network_insights_sector", "network_insights", ["sector"])
    op.create_index("ix_network_insights_active", "network_insights", ["is_active", "insight_type"])


def downgrade():
    op.drop_table("network_insights")
