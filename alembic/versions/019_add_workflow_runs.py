"""Add workflow_runs table for LangGraph workflow execution tracking

Revision ID: 019
Revises: 018
Create Date: 2025-02-04

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '019'
down_revision = '018'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'workflow_runs',
        # Primary key
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),

        # Workflow identification
        sa.Column('workflow_name', sa.String(), nullable=False),
        sa.Column('workflow_version', sa.String(), nullable=True),

        # Execution status
        sa.Column('status', sa.String(), nullable=False, server_default='queued'),

        # Timestamps
        sa.Column('queued_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),

        # Input/Output data
        sa.Column('inputs', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('outputs', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),

        # State tracking for LangGraph checkpoints
        sa.Column('state', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),

        # Error tracking
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_traceback', sa.Text(), nullable=True),

        # Human-in-the-loop review
        sa.Column('review_required', sa.String(), nullable=True),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_decision', sa.String(), nullable=True),

        # Metadata
        sa.Column('triggered_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('run_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),

        # Standard timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        # Primary key constraint
        sa.PrimaryKeyConstraint('id'),

        # Foreign key constraints
        sa.ForeignKeyConstraint(['triggered_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),

        # Check constraints
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'needs_review', 'completed', 'failed', 'cancelled')",
            name='ck_workflow_run_status'
        ),
        sa.CheckConstraint(
            "review_decision IS NULL OR review_decision IN ('approved', 'rejected', 'modified')",
            name='ck_workflow_run_review_decision'
        ),
    )

    # Create indexes
    op.create_index('ix_workflow_runs_workflow_name', 'workflow_runs', ['workflow_name'])
    op.create_index('ix_workflow_runs_status', 'workflow_runs', ['status'])
    op.create_index('ix_workflow_runs_queued_at', 'workflow_runs', ['queued_at'])
    op.create_index('ix_workflow_runs_triggered_by', 'workflow_runs', ['triggered_by'])
    op.create_index('ix_workflow_runs_reviewed_by', 'workflow_runs', ['reviewed_by'])


def downgrade():
    op.drop_index('ix_workflow_runs_reviewed_by', table_name='workflow_runs')
    op.drop_index('ix_workflow_runs_triggered_by', table_name='workflow_runs')
    op.drop_index('ix_workflow_runs_queued_at', table_name='workflow_runs')
    op.drop_index('ix_workflow_runs_status', table_name='workflow_runs')
    op.drop_index('ix_workflow_runs_workflow_name', table_name='workflow_runs')
    op.drop_table('workflow_runs')
