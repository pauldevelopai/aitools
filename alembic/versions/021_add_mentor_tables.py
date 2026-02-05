"""Add mentor workflow tables (tasks, artifacts, sessions)

Revision ID: 021
Revises: 020
Create Date: 2025-02-04

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '021'
down_revision = '020'
branch_labels = None
depends_on = None


def upgrade():
    # Create mentor_tasks table
    op.create_table(
        'mentor_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),

        # Parent engagement
        sa.Column('engagement_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Task details
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('task_type', sa.String(50), nullable=False, server_default='action'),

        # Status tracking
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='2'),

        # Assignment
        sa.Column('assigned_to', sa.String(255), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),

        # Completion
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completion_notes', sa.Text(), nullable=True),

        # Decision tracking
        sa.Column('decision_made', sa.Text(), nullable=True),
        sa.Column('decision_rationale', sa.Text(), nullable=True),

        # Workflow tracking
        sa.Column('created_by_workflow', sa.String(100), nullable=True),
        sa.Column('workflow_run_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Ordering
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['engagement_id'], ['engagements.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workflow_run_id'], ['workflow_runs.id'], ondelete='SET NULL'),
        sa.CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed', 'deferred', 'cancelled')",
            name='ck_mentor_task_status'
        ),
        sa.CheckConstraint(
            "task_type IN ('action', 'decision', 'blocker', 'learning', 'deliverable')",
            name='ck_mentor_task_type'
        ),
        sa.CheckConstraint(
            'priority >= 1 AND priority <= 5',
            name='ck_mentor_task_priority'
        ),
    )

    op.create_index('ix_mentor_tasks_engagement_id', 'mentor_tasks', ['engagement_id'])
    op.create_index('ix_mentor_tasks_status', 'mentor_tasks', ['status'])
    op.create_index('ix_mentor_tasks_workflow_run_id', 'mentor_tasks', ['workflow_run_id'])

    # Create mentor_artifacts table
    op.create_table(
        'mentor_artifacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),

        # Parent engagement
        sa.Column('engagement_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Artifact identification
        sa.Column('artifact_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),

        # Versioning
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default='true'),

        # Content
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_format', sa.String(20), nullable=False, server_default='markdown'),

        # Structured data
        sa.Column('structured_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),

        # Source tracking
        sa.Column('source_notes', sa.Text(), nullable=True),
        sa.Column('source_file_url', sa.String(500), nullable=True),

        # Workflow tracking
        sa.Column('created_by_workflow', sa.String(100), nullable=True),
        sa.Column('workflow_run_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['engagement_id'], ['engagements.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workflow_run_id'], ['workflow_runs.id'], ondelete='SET NULL'),
        sa.CheckConstraint(
            "artifact_type IN ('prototype_charter', 'session_agenda', 'prototype_pack', 'decision_log', 'transcript', 'notes')",
            name='ck_mentor_artifact_type'
        ),
        sa.CheckConstraint(
            "content_format IN ('markdown', 'html', 'json', 'text')",
            name='ck_mentor_artifact_format'
        ),
    )

    op.create_index('ix_mentor_artifacts_engagement_id', 'mentor_artifacts', ['engagement_id'])
    op.create_index('ix_mentor_artifacts_artifact_type', 'mentor_artifacts', ['artifact_type'])
    op.create_index('ix_mentor_artifacts_workflow_run_id', 'mentor_artifacts', ['workflow_run_id'])

    # Create mentor_sessions table
    op.create_table(
        'mentor_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),

        # Parent engagement
        sa.Column('engagement_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Session identification
        sa.Column('session_number', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('session_type', sa.String(50), nullable=False, server_default='regular'),

        # Timing
        sa.Column('scheduled_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),

        # Status
        sa.Column('status', sa.String(50), nullable=False, server_default='scheduled'),

        # Notes and outcomes
        sa.Column('agenda', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('key_decisions', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('action_items', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),

        # Workflow tracking
        sa.Column('workflow_run_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['engagement_id'], ['engagements.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workflow_run_id'], ['workflow_runs.id'], ondelete='SET NULL'),
        sa.CheckConstraint(
            "status IN ('scheduled', 'completed', 'cancelled', 'rescheduled')",
            name='ck_mentor_session_status'
        ),
        sa.CheckConstraint(
            "session_type IN ('intake', 'regular', 'review', 'final')",
            name='ck_mentor_session_type'
        ),
    )

    op.create_index('ix_mentor_sessions_engagement_id', 'mentor_sessions', ['engagement_id'])
    op.create_index('ix_mentor_sessions_status', 'mentor_sessions', ['status'])
    op.create_index('ix_mentor_sessions_workflow_run_id', 'mentor_sessions', ['workflow_run_id'])


def downgrade():
    # Drop mentor_sessions
    op.drop_index('ix_mentor_sessions_workflow_run_id', table_name='mentor_sessions')
    op.drop_index('ix_mentor_sessions_status', table_name='mentor_sessions')
    op.drop_index('ix_mentor_sessions_engagement_id', table_name='mentor_sessions')
    op.drop_table('mentor_sessions')

    # Drop mentor_artifacts
    op.drop_index('ix_mentor_artifacts_workflow_run_id', table_name='mentor_artifacts')
    op.drop_index('ix_mentor_artifacts_artifact_type', table_name='mentor_artifacts')
    op.drop_index('ix_mentor_artifacts_engagement_id', table_name='mentor_artifacts')
    op.drop_table('mentor_artifacts')

    # Drop mentor_tasks
    op.drop_index('ix_mentor_tasks_workflow_run_id', table_name='mentor_tasks')
    op.drop_index('ix_mentor_tasks_status', table_name='mentor_tasks')
    op.drop_index('ix_mentor_tasks_engagement_id', table_name='mentor_tasks')
    op.drop_table('mentor_tasks')
