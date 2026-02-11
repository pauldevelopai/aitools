"""Add spreadsheet_imports table and client_id to media_organizations

Revision ID: 031
Revises: 030
Create Date: 2026-02-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers
revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create spreadsheet_imports table
    op.create_table(
        "spreadsheet_imports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("file_type", sa.String(10), nullable=False),
        sa.Column("row_count", sa.Integer, default=0),
        sa.Column("raw_headers", JSONB, server_default="[]"),
        sa.Column("sample_rows", JSONB, server_default="[]"),
        sa.Column("column_mapping", JSONB, server_default="{}"),
        sa.Column("field_defaults", JSONB, server_default="{}"),
        sa.Column("chat_history", JSONB, server_default="[]"),
        sa.Column("status", sa.String(20), nullable=False, server_default="uploaded"),
        sa.Column("records_created", sa.Integer, default=0),
        sa.Column("records_updated", sa.Integer, default=0),
        sa.Column("records_skipped", sa.Integer, default=0),
        sa.Column("import_errors", JSONB, server_default="[]"),
        sa.Column("uploaded_by_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("organization_profiles.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Add client_id to media_organizations
    op.add_column(
        "media_organizations",
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("organization_profiles.id", ondelete="SET NULL"), nullable=True, index=True),
    )


def downgrade() -> None:
    op.drop_column("media_organizations", "client_id")
    op.drop_table("spreadsheet_imports")
