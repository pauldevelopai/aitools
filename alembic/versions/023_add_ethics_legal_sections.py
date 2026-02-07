"""Add ethics_policy and legal_framework to content_items section constraint

Revision ID: 023
Revises: 022
Create Date: 2026-02-07 00:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '023'
down_revision = '022'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old constraint and add updated one with new section values
    op.drop_constraint('ck_content_items_section', 'content_items', type_='check')
    op.create_check_constraint(
        'ck_content_items_section',
        'content_items',
        "section IN ('foundations', 'resources', 'governance', 'tools', 'use-cases', 'ethics_policy', 'legal_framework')"
    )


def downgrade() -> None:
    op.drop_constraint('ck_content_items_section', 'content_items', type_='check')
    op.create_check_constraint(
        'ck_content_items_section',
        'content_items',
        "section IN ('foundations', 'resources', 'governance', 'tools', 'use-cases')"
    )
