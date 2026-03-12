"""Add user_progress table for tracking AI implementation progress.

Revision ID: 037
Revises: 036
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "037"
down_revision = "036"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_progress",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True),
        sa.Column("ethics_policy_complete", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("legal_framework_complete", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("strategy_plan_complete", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("readiness_assessment_complete", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("tools_evaluated_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("overall_completion_pct", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("completed_items", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade():
    op.drop_table("user_progress")
