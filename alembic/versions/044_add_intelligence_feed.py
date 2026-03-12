"""Add feed_items and user_feed_reads tables for intelligence feed.

Revision ID: 044
Revises: 043
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "044"
down_revision = "043"
branch_labels = None
depends_on = None


def upgrade():
    # ---- feed_items ----
    op.create_table(
        "feed_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), unique=True, nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content_markdown", sa.Text(), nullable=True),
        sa.Column("feed_category", sa.String(), nullable=False),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("source_name", sa.String(), nullable=True),
        sa.Column("jurisdiction", sa.String(), nullable=True),
        sa.Column("sectors", postgresql.JSONB(), nullable=True, server_default="[]"),
        sa.Column("tags", postgresql.JSONB(), nullable=True, server_default="[]"),
        sa.Column("relevance_score", sa.Float(), nullable=True, server_default="0.5"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("generated_by_run_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("brain_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "feed_category IN ('regulation', 'ethics', 'security', 'tool_update', 'sector_news', 'platform_update')",
            name="ck_feed_items_category",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_feed_items_status",
        ),
    )
    op.create_index("ix_feed_items_slug", "feed_items", ["slug"])
    op.create_index("ix_feed_items_category", "feed_items", ["feed_category"])
    op.create_index("ix_feed_items_status", "feed_items", ["status"])
    op.create_index("ix_feed_items_published_at", "feed_items", ["published_at"])

    # ---- user_feed_reads ----
    op.create_table(
        "user_feed_reads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("feed_item_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("feed_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "feed_item_id", name="uq_user_feed_read"),
    )
    op.create_index("ix_user_feed_reads_user_id", "user_feed_reads", ["user_id"])
    op.create_index("ix_user_feed_reads_feed_item_id", "user_feed_reads", ["feed_item_id"])


def downgrade():
    op.drop_table("user_feed_reads")
    op.drop_table("feed_items")
