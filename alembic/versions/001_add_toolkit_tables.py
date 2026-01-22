"""add toolkit tables

Revision ID: 001
Revises:
Create Date: 2026-01-22

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Create toolkit_documents table
    op.create_table(
        'toolkit_documents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('version_tag', sa.String(), nullable=False),
        sa.Column('source_filename', sa.String(), nullable=False),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('upload_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('chunk_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
    )
    op.create_index('ix_toolkit_documents_version_tag', 'toolkit_documents', ['version_tag'], unique=True)

    # Create toolkit_chunks table
    op.create_table(
        'toolkit_chunks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', UUID(as_uuid=True), sa.ForeignKey('toolkit_documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('heading', sa.String(), nullable=True),
        sa.Column('metadata', JSONB, nullable=True),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_toolkit_chunks_document_id', 'toolkit_chunks', ['document_id'])


def downgrade() -> None:
    op.drop_table('toolkit_chunks')
    op.drop_table('toolkit_documents')
    op.execute('DROP EXTENSION IF EXISTS vector')
