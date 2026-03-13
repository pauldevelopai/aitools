"""Add audit_scores and time_dividend_entries tables.

Revision ID: 049
Revises: 048
Create Date: 2026-03-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers
revision = '049'
down_revision = '048'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Audit scores table
    op.create_table(
        'audit_scores',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('tool_slug', sa.String(200), nullable=False, index=True),
        sa.Column('data_sovereignty', sa.Integer(), nullable=False),
        sa.Column('exportability', sa.Integer(), nullable=False),
        sa.Column('business_model', sa.Integer(), nullable=False),
        sa.Column('security', sa.Integer(), nullable=False),
        sa.Column('total_score', sa.Integer(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('user_id', 'tool_slug', name='uq_audit_scores_user_tool'),
        sa.CheckConstraint('data_sovereignty >= 0 AND data_sovereignty <= 5', name='ck_audit_sovereignty_range'),
        sa.CheckConstraint('exportability >= 0 AND exportability <= 5', name='ck_audit_exportability_range'),
        sa.CheckConstraint('business_model >= 0 AND business_model <= 5', name='ck_audit_business_model_range'),
        sa.CheckConstraint('security >= 0 AND security <= 5', name='ck_audit_security_range'),
        sa.CheckConstraint('total_score >= 0 AND total_score <= 20', name='ck_audit_total_range'),
    )

    # Time dividend entries table
    op.create_table(
        'time_dividend_entries',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('tool_slug', sa.String(200), nullable=False, index=True),
        sa.Column('hours_saved_weekly', sa.Float(), nullable=False),
        sa.Column('reinvestment_category', sa.String(100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('user_id', 'tool_slug', name='uq_time_dividend_user_tool'),
        sa.CheckConstraint('hours_saved_weekly >= 0', name='ck_time_dividend_hours_positive'),
    )


def downgrade() -> None:
    op.drop_table('time_dividend_entries')
    op.drop_table('audit_scores')
