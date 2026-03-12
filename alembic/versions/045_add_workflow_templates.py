"""Add workflow_templates table with seed data, and template_id column on workflow_runs.

Revision ID: 045
Revises: 044
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "045"
down_revision = "044"
branch_labels = None
depends_on = None


def upgrade():
    # ---- workflow_templates ----
    op.create_table(
        "workflow_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("slug", sa.String(), unique=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("steps", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("input_schema", postgresql.JSONB(), nullable=True, server_default="{}"),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column("difficulty", sa.String(), nullable=False, server_default="beginner"),
        sa.Column("sectors", postgresql.JSONB(), nullable=True, server_default="[]"),
        sa.Column("tags", postgresql.JSONB(), nullable=True, server_default="[]"),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "category IN ('content_production', 'research', 'governance', 'audience', 'operations')",
            name="ck_workflow_templates_category",
        ),
        sa.CheckConstraint(
            "difficulty IN ('beginner', 'intermediate', 'advanced')",
            name="ck_workflow_templates_difficulty",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_workflow_templates_status",
        ),
    )
    op.create_index("ix_workflow_templates_slug", "workflow_templates", ["slug"])
    op.create_index("ix_workflow_templates_category", "workflow_templates", ["category"])
    op.create_index("ix_workflow_templates_status", "workflow_templates", ["status"])

    # ---- Add template_id FK to existing workflow_runs ----
    op.add_column(
        "workflow_runs",
        sa.Column(
            "template_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflow_templates.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # ---- Seed starter templates ----
    templates_tbl = sa.table(
        "workflow_templates",
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("category", sa.String),
        sa.column("steps", postgresql.JSONB),
        sa.column("estimated_minutes", sa.Integer),
        sa.column("difficulty", sa.String),
        sa.column("sectors", postgresql.JSONB),
        sa.column("tags", postgresql.JSONB),
        sa.column("is_featured", sa.Boolean),
        sa.column("status", sa.String),
    )

    op.bulk_insert(templates_tbl, [
        {
            "slug": "fact-check-claim",
            "name": "Fact-Check a Claim",
            "description": "A structured workflow for verifying claims using existing resources and trusted sources.",
            "category": "research",
            "steps": [
                {"order": 1, "name": "Identify the Claim", "description": "Clearly state the claim to be checked and note its source.", "tool_or_action": "manual", "config": {}},
                {"order": 2, "name": "Search Existing Resources", "description": "Search the platform library and external sources for relevant information.", "tool_or_action": "library_search", "config": {}},
                {"order": 3, "name": "Evaluate Sources", "description": "Rate the credibility of each source found using the CDI framework.", "tool_or_action": "cdi_evaluation", "config": {}},
                {"order": 4, "name": "Draft Summary", "description": "Write a summary of your findings with a verdict and supporting evidence.", "tool_or_action": "manual", "config": {}},
            ],
            "estimated_minutes": 20,
            "difficulty": "beginner",
            "sectors": (["newsroom", "ngo"]),
            "tags": (["verification", "research", "fact-checking"]),
            "is_featured": True,
            "status": "published",
        },
        {
            "slug": "draft-ai-use-policy",
            "name": "Draft an AI Use Policy",
            "description": "Step-by-step guidance for creating an organisational AI use policy.",
            "category": "governance",
            "steps": ([
                {"order": 1, "name": "Assess Current AI Use", "description": "Complete the AI Readiness Assessment to understand your starting point.", "tool_or_action": "readiness_assessment", "config": {}},
                {"order": 2, "name": "Review Ethics Frameworks", "description": "Review relevant ethics policies and frameworks in the library.", "tool_or_action": "ethics_review", "config": {}},
                {"order": 3, "name": "Draft Policy Sections", "description": "Use the Policy Builder to draft permitted, restricted, and prohibited uses.", "tool_or_action": "policy_builder", "config": {}},
                {"order": 4, "name": "Internal Review", "description": "Share the draft with stakeholders for feedback and iterate.", "tool_or_action": "manual", "config": {}},
            ]),
            "estimated_minutes": 45,
            "difficulty": "intermediate",
            "sectors": (["newsroom", "ngo", "law_firm", "business"]),
            "tags": (["policy", "governance", "ethics"]),
            "is_featured": True,
            "status": "published",
        },
        {
            "slug": "research-new-ai-tool",
            "name": "Research a New AI Tool",
            "description": "Evaluate whether a new AI tool is suitable for your organisation.",
            "category": "research",
            "steps": ([
                {"order": 1, "name": "Search the Directory", "description": "Check if the tool is already in the platform directory with reviews and CDI scores.", "tool_or_action": "tool_search", "config": {}},
                {"order": 2, "name": "Check Reviews", "description": "Read existing peer reviews and check for red flags.", "tool_or_action": "review_check", "config": {}},
                {"order": 3, "name": "Evaluate Fit", "description": "Score the tool against your strategy priorities and needs.", "tool_or_action": "strategy_match", "config": {}},
                {"order": 4, "name": "Add to Watchlist", "description": "Add the tool to your toolkit or flag for further review.", "tool_or_action": "manual", "config": {}},
            ]),
            "estimated_minutes": 15,
            "difficulty": "beginner",
            "sectors": (["newsroom", "ngo", "law_firm", "business"]),
            "tags": (["tools", "evaluation", "research"]),
            "is_featured": True,
            "status": "published",
        },
        {
            "slug": "legal-compliance-review",
            "name": "Prepare a Legal Compliance Review",
            "description": "Review your AI tool usage against relevant legal and regulatory frameworks.",
            "category": "governance",
            "steps": ([
                {"order": 1, "name": "Identify Jurisdiction", "description": "Determine which legal jurisdictions apply to your organisation.", "tool_or_action": "manual", "config": {}},
                {"order": 2, "name": "Review Frameworks", "description": "Review applicable legal frameworks (GDPR, EU AI Act, etc.) in the library.", "tool_or_action": "framework_review", "config": {}},
                {"order": 3, "name": "Compliance Checklist", "description": "Work through the compliance checklist for each framework.", "tool_or_action": "legal_builder", "config": {}},
                {"order": 4, "name": "Draft Narrative", "description": "Write a narrative summary of compliance status and action items.", "tool_or_action": "manual", "config": {}},
            ]),
            "estimated_minutes": 60,
            "difficulty": "advanced",
            "sectors": (["law_firm", "business", "ngo"]),
            "tags": (["legal", "compliance", "governance", "gdpr"]),
            "is_featured": False,
            "status": "published",
        },
        {
            "slug": "analyse-audience-engagement",
            "name": "Analyse Audience Engagement",
            "description": "Use AI tools to understand and improve audience engagement patterns.",
            "category": "audience",
            "steps": ([
                {"order": 1, "name": "Define Metrics", "description": "Identify the key engagement metrics relevant to your organisation.", "tool_or_action": "manual", "config": {}},
                {"order": 2, "name": "Gather Data", "description": "Collect engagement data from your platforms and tools.", "tool_or_action": "manual", "config": {}},
                {"order": 3, "name": "Identify Patterns", "description": "Use AI analysis tools to find patterns and trends in the data.", "tool_or_action": "ai_analysis", "config": {}},
                {"order": 4, "name": "Draft Recommendations", "description": "Summarise findings and write actionable recommendations.", "tool_or_action": "manual", "config": {}},
            ]),
            "estimated_minutes": 30,
            "difficulty": "intermediate",
            "sectors": (["newsroom", "ngo"]),
            "tags": (["audience", "analytics", "engagement"]),
            "is_featured": False,
            "status": "published",
        },
    ])


def downgrade():
    op.drop_column("workflow_runs", "template_id")
    op.drop_table("workflow_templates")
