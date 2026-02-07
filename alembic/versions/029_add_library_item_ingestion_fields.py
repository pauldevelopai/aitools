"""Add source_id and content_hash to library_items for dedup/re-ingest

Revision ID: 029
Revises: 028
Create Date: 2026-02-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '029'
down_revision = '028'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('library_items', sa.Column('source_id', sa.String(), nullable=True))
    op.add_column('library_items', sa.Column('content_hash', sa.String(64), nullable=True))
    op.create_index('ix_library_items_source_id', 'library_items', ['source_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_library_items_source_id', table_name='library_items')
    op.drop_column('library_items', 'content_hash')
    op.drop_column('library_items', 'source_id')
