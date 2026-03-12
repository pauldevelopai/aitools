"""Add Brain self-improvement tables: knowledge_gaps, content_quality_scores, brain_runs.

Revision ID: 035
Revises: 034
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "035"
down_revision = "034"
branch_labels = None
depends_on = None


def upgrade():
    # knowledge_gaps
    op.create_table(
        "knowledge_gaps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("topic", sa.String(), nullable=False, index=True),
        sa.Column("sector", sa.String(), nullable=True),
        sa.Column("gap_type", sa.String(), nullable=False, server_default="no_content"),
        sa.Column("detected_from", sa.String(), nullable=False),
        sa.Column("detection_details", postgresql.JSONB(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("status", sa.String(), nullable=False, server_default="open", index=True),
        sa.Column("filled_by_content_id", sa.String(), nullable=True),
        sa.Column("filled_by_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "gap_type IN ('no_content', 'low_quality', 'stale', 'user_requested')",
            name="ck_knowledge_gap_type",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'researching', 'filled', 'dismissed')",
            name="ck_knowledge_gap_status",
        ),
        sa.CheckConstraint(
            "priority BETWEEN 1 AND 5",
            name="ck_knowledge_gap_priority",
        ),
    )

    # content_quality_scores
    op.create_table(
        "content_quality_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("content_type", sa.String(), nullable=False, index=True),
        sa.Column("content_id", sa.String(), nullable=False, index=True),
        sa.Column("positive_feedback_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("negative_feedback_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_similarity_when_used", sa.Float(), nullable=True),
        sa.Column("times_cited", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("staleness_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("overall_quality_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # brain_runs
    op.create_table(
        "brain_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mission_type", sa.String(), nullable=False, index=True),
        sa.Column("trigger", sa.String(), nullable=False, server_default="admin"),
        sa.Column("input_params", postgresql.JSONB(), nullable=True),
        sa.Column("tool_calls", postgresql.JSONB(), nullable=True),
        sa.Column("records_created", postgresql.JSONB(), nullable=True),
        sa.Column("quality_assessment", postgresql.JSONB(), nullable=True),
        sa.Column("tokens_used", postgresql.JSONB(), nullable=True),
        sa.Column("research_notes", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="running", index=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "workflow_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflow_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'failed')",
            name="ck_brain_run_status",
        ),
    )


def downgrade():
    op.drop_table("brain_runs")
    op.drop_table("content_quality_scores")
    op.drop_table("knowledge_gaps")
