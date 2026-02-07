"""Add library_items table

Revision ID: 028
Revises: 027
Create Date: 2026-02-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '028'
down_revision = '027'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'library_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('document_type', sa.String(), nullable=False, index=True),
        sa.Column('jurisdiction', sa.String(), nullable=True, index=True),
        sa.Column('tags', postgresql.JSONB(), nullable=True),
        sa.Column('publisher', sa.String(), nullable=True),
        sa.Column('publication_date', sa.Date(), nullable=True),
        sa.Column('source_url', sa.String(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('content_markdown', sa.Text(), nullable=False),
        sa.Column('sections', postgresql.JSONB(), nullable=True),
        sa.Column('is_published', sa.Boolean(), nullable=False, default=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "document_type IN ('regulation', 'policy', 'guidance', 'standard', 'framework')",
            name='ck_library_items_document_type',
        ),
    )
    op.create_index(
        'ix_library_items_type_jurisdiction',
        'library_items',
        ['document_type', 'jurisdiction'],
    )


def downgrade() -> None:
    op.drop_index('ix_library_items_type_jurisdiction', table_name='library_items')
    op.drop_table('library_items')
