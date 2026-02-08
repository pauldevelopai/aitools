"""Add google_connections and google_sync_items tables

Revision ID: 030
Revises: 029
Create Date: 2026-02-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '030'
down_revision = '029'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Google OAuth connections (one per admin user)
    op.create_table(
        'google_connections',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('access_token_encrypted', sa.Text(), nullable=False),
        sa.Column('refresh_token_encrypted', sa.Text(), nullable=False),
        sa.Column('token_expiry', sa.DateTime(timezone=True), nullable=True),
        sa.Column('google_email', sa.String(), nullable=True),
        sa.Column('scopes', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Synced Google Drive files
    op.create_table(
        'google_sync_items',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('connection_id', UUID(as_uuid=True), sa.ForeignKey('google_connections.id', ondelete='CASCADE'), nullable=False),
        sa.Column('google_file_id', sa.String(), nullable=False, index=True),
        sa.Column('google_file_name', sa.String(), nullable=False),
        sa.Column('google_mime_type', sa.String(), nullable=True),
        sa.Column('google_parent_id', sa.String(), nullable=True),
        sa.Column('target_type', sa.String(), nullable=False),
        sa.Column('target_id', UUID(as_uuid=True), nullable=True),
        sa.Column('sync_status', sa.String(), nullable=False, server_default=sa.text("'pending'")),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('content_hash', sa.String(64), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('library_item_id', UUID(as_uuid=True), sa.ForeignKey('library_items.id', ondelete='SET NULL'), nullable=True),
        sa.Column('toolkit_document_id', UUID(as_uuid=True), sa.ForeignKey('toolkit_documents.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('connection_id', 'google_file_id', name='uq_sync_connection_file'),
        sa.CheckConstraint("target_type IN ('library', 'organization')", name='ck_sync_items_target_type'),
        sa.CheckConstraint("sync_status IN ('pending', 'syncing', 'synced', 'error')", name='ck_sync_items_sync_status'),
    )


def downgrade() -> None:
    op.drop_table('google_sync_items')
    op.drop_table('google_connections')
