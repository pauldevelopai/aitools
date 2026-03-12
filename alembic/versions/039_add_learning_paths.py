"""Add learning_paths and user_path_enrollments tables with seed data.

Revision ID: 039
Revises: 038
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "039"
down_revision = "038"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "learning_paths",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("slug", sa.String(), unique=True, nullable=False, index=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sector", sa.String(), nullable=True),
        sa.Column("difficulty", sa.String(), nullable=False, server_default="beginner"),
        sa.Column("steps", postgresql.JSONB(), nullable=False),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "user_path_enrollments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("path_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("completed_steps", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("completion_pct", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "path_id", name="uq_user_path"),
    )

    # Seed default learning paths
    paths = sa.table(
        "learning_paths",
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("sector", sa.String),
        sa.column("difficulty", sa.String),
        sa.column("steps", postgresql.JSONB),
        sa.column("estimated_minutes", sa.Integer),
    )

    op.bulk_insert(paths, [
        {
            "slug": "newsroom-ai-starter",
            "name": "Newsroom AI Starter",
            "description": "A step-by-step introduction to implementing AI responsibly in your newsroom.",
            "sector": "newsroom",
            "difficulty": "beginner",
            "estimated_minutes": 90,
            "steps": [
                {"id": "s1", "title": "Read AI Foundations", "description": "Learn the basics of AI in journalism", "action_url": "/foundations", "order": 1},
                {"id": "s2", "title": "Take Readiness Assessment", "description": "Discover where your newsroom stands", "action_url": "/readiness", "order": 2},
                {"id": "s3", "title": "Build Ethics Policy", "description": "Create an AI ethics policy for your newsroom", "action_url": "/ethics-builder", "order": 3},
                {"id": "s4", "title": "Explore AI Tools", "description": "Browse verified AI tools for journalism", "action_url": "/tools", "order": 4},
                {"id": "s5", "title": "Build Strategy Plan", "description": "Get a personalised implementation roadmap", "action_url": "/strategy", "order": 5},
                {"id": "s6", "title": "Export Your Report", "description": "Download your complete AI implementation report", "action_url": "/export", "order": 6},
            ],
        },
        {
            "slug": "ngo-ethics-first",
            "name": "NGO Ethics-First Path",
            "description": "Start with ethics and compliance, then move to tools and strategy for your NGO.",
            "sector": "ngo",
            "difficulty": "beginner",
            "estimated_minutes": 75,
            "steps": [
                {"id": "s1", "title": "Ethics Foundations", "description": "Understand AI ethics principles for the development sector", "action_url": "/foundations", "order": 1},
                {"id": "s2", "title": "Build Ethics Policy", "description": "Create a policy tailored for NGO data sensitivity", "action_url": "/ethics-builder", "order": 2},
                {"id": "s3", "title": "Build Legal Framework", "description": "Understand your regulatory requirements", "action_url": "/legal-builder", "order": 3},
                {"id": "s4", "title": "Evaluate AI Tools", "description": "Find tools that respect beneficiary privacy", "action_url": "/tools", "order": 4},
                {"id": "s5", "title": "Build Strategy Plan", "description": "Plan your AI adoption with ethics at the centre", "action_url": "/strategy", "order": 5},
            ],
        },
        {
            "slug": "law-firm-compliance",
            "name": "Law Firm Compliance Path",
            "description": "A compliance-focused AI adoption journey for legal practices.",
            "sector": "law_firm",
            "difficulty": "intermediate",
            "estimated_minutes": 80,
            "steps": [
                {"id": "s1", "title": "Legal AI Foundations", "description": "Understand AI in legal practice and regulation", "action_url": "/foundations", "order": 1},
                {"id": "s2", "title": "Build Legal Framework", "description": "Map your regulatory obligations", "action_url": "/legal-builder", "order": 2},
                {"id": "s3", "title": "Build Ethics Policy", "description": "Create client-confidentiality-aware AI guidelines", "action_url": "/ethics-builder", "order": 3},
                {"id": "s4", "title": "Assess AI Tools", "description": "Evaluate tools for legal research and contract review", "action_url": "/tools", "order": 4},
                {"id": "s5", "title": "Build Strategy Plan", "description": "Plan AI adoption with compliance as priority", "action_url": "/strategy", "order": 5},
            ],
        },
        {
            "slug": "business-ai-adoption",
            "name": "Business AI Adoption",
            "description": "A practical path to implementing AI across your business operations.",
            "sector": "business",
            "difficulty": "beginner",
            "estimated_minutes": 70,
            "steps": [
                {"id": "s1", "title": "Take Readiness Assessment", "description": "Benchmark your AI maturity", "action_url": "/readiness", "order": 1},
                {"id": "s2", "title": "Read AI Foundations", "description": "Build foundational AI knowledge", "action_url": "/foundations", "order": 2},
                {"id": "s3", "title": "Explore AI Tools", "description": "Find tools for operations, HR, and customer service", "action_url": "/tools", "order": 3},
                {"id": "s4", "title": "Build Strategy Plan", "description": "Create an AI implementation roadmap with ROI focus", "action_url": "/strategy", "order": 4},
                {"id": "s5", "title": "View Benchmarking", "description": "See how you compare to similar organisations", "action_url": "/benchmarking", "order": 5},
            ],
        },
    ])


def downgrade():
    op.drop_table("user_path_enrollments")
    op.drop_table("learning_paths")
