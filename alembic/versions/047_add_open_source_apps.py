"""Add open_source_apps table for the curated app directory.

Revision ID: 047
Revises: 046
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "047"
down_revision = "046"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "open_source_apps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("slug", sa.String(), unique=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("github_url", sa.String(), nullable=False),
        sa.Column("website_url", sa.String(), nullable=True),
        sa.Column("docs_url", sa.String(), nullable=True),
        sa.Column("categories", postgresql.JSONB(), nullable=True, server_default="[]"),
        sa.Column("tags", postgresql.JSONB(), nullable=True, server_default="[]"),
        sa.Column("sectors", postgresql.JSONB(), nullable=True, server_default="[]"),
        sa.Column("license_type", sa.String(), nullable=False, server_default="MIT"),
        sa.Column("deployment_type", sa.String(), nullable=False, server_default="self_hosted"),
        sa.Column("installation_guide", sa.Text(), nullable=True),
        sa.Column("system_requirements", sa.Text(), nullable=True),
        sa.Column("platforms", postgresql.JSONB(), nullable=True, server_default="[]"),
        sa.Column("difficulty", sa.String(), nullable=False, server_default="beginner"),
        sa.Column("pricing_model", sa.String(), nullable=False, server_default="free"),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "deployment_type IN ('self_hosted', 'cloud', 'hybrid', 'desktop')",
            name="ck_open_source_apps_deployment_type",
        ),
        sa.CheckConstraint(
            "difficulty IN ('beginner', 'intermediate', 'advanced')",
            name="ck_open_source_apps_difficulty",
        ),
        sa.CheckConstraint(
            "pricing_model IN ('free', 'freemium', 'open_core')",
            name="ck_open_source_apps_pricing_model",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_open_source_apps_status",
        ),
    )
    op.create_index("ix_open_source_apps_slug", "open_source_apps", ["slug"])
    op.create_index("ix_open_source_apps_deployment_type", "open_source_apps", ["deployment_type"])
    op.create_index("ix_open_source_apps_status", "open_source_apps", ["status"])


def downgrade():
    op.drop_table("open_source_apps")
