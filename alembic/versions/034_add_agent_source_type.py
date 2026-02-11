"""Add 'agent' to discovered_tools source_type and 'in_kit' to status constraints.

Revision ID: 034
Revises: 033
"""
from alembic import op

revision = "034"
down_revision = "033"
branch_labels = None
depends_on = None


def upgrade():
    # Drop and recreate source_type CHECK constraint to include 'agent'
    op.drop_constraint("ck_discovered_tool_source_type", "discovered_tools", type_="check")
    op.create_check_constraint(
        "ck_discovered_tool_source_type",
        "discovered_tools",
        "source_type IN ('github', 'producthunt', 'awesome_list', 'directory', 'agent')",
    )

    # Drop and recreate status CHECK constraint to include 'in_kit'
    op.drop_constraint("ck_discovered_tool_status", "discovered_tools", type_="check")
    op.create_check_constraint(
        "ck_discovered_tool_status",
        "discovered_tools",
        "status IN ('pending_review', 'approved', 'rejected', 'archived', 'in_kit')",
    )


def downgrade():
    op.drop_constraint("ck_discovered_tool_status", "discovered_tools", type_="check")
    op.create_check_constraint(
        "ck_discovered_tool_status",
        "discovered_tools",
        "status IN ('pending_review', 'approved', 'rejected', 'archived')",
    )

    op.drop_constraint("ck_discovered_tool_source_type", "discovered_tools", type_="check")
    op.create_check_constraint(
        "ck_discovered_tool_source_type",
        "discovered_tools",
        "source_type IN ('github', 'producthunt', 'awesome_list', 'directory')",
    )
