"""Add data_assets and license_inquiries tables for data registry.

Revision ID: 046
Revises: 045
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "046"
down_revision = "045"
branch_labels = None
depends_on = None


def upgrade():
    # ---- data_assets ----
    op.create_table(
        "data_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("asset_type", sa.String(), nullable=False),
        sa.Column("data_format", sa.String(), nullable=True),
        sa.Column("record_count", sa.Integer(), nullable=True),
        sa.Column("date_range_start", sa.Date(), nullable=True),
        sa.Column("date_range_end", sa.Date(), nullable=True),
        sa.Column("languages", postgresql.JSONB(), nullable=True, server_default="[]"),
        sa.Column("sectors", postgresql.JSONB(), nullable=True, server_default="[]"),
        sa.Column("tags", postgresql.JSONB(), nullable=True, server_default="[]"),
        sa.Column("classification", sa.String(), nullable=False, server_default="internal"),
        sa.Column("is_licensable", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("licensing_terms", sa.Text(), nullable=True),
        sa.Column("contact_email", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "asset_type IN ('archive', 'dataset', 'api', 'feed', 'document_collection')",
            name="ck_data_assets_type",
        ),
        sa.CheckConstraint(
            "classification IN ('public', 'internal', 'confidential')",
            name="ck_data_assets_classification",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'archived')",
            name="ck_data_assets_status",
        ),
    )
    op.create_index("ix_data_assets_slug", "data_assets", ["slug"])
    op.create_index("ix_data_assets_type", "data_assets", ["asset_type"])
    op.create_index("ix_data_assets_status", "data_assets", ["status"])
    op.create_index("ix_data_assets_created_by", "data_assets", ["created_by"])

    # ---- license_inquiries ----
    op.create_table(
        "license_inquiries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("data_assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requester_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'responded', 'declined')",
            name="ck_license_inquiries_status",
        ),
    )
    op.create_index("ix_license_inquiries_asset_id", "license_inquiries", ["asset_id"])
    op.create_index("ix_license_inquiries_requester_id", "license_inquiries", ["requester_id"])


def downgrade():
    op.drop_table("license_inquiries")
    op.drop_table("data_assets")
