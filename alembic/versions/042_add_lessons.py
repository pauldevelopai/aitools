"""Add lesson_modules, lessons, user_lesson_progress, user_tokens,
token_transactions tables with seed data for starter modules.

Revision ID: 042
Revises: 041
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "042"
down_revision = "041"
branch_labels = None
depends_on = None


def upgrade():
    # ---- lesson_modules ----
    op.create_table(
        "lesson_modules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("slug", sa.String(), unique=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sector", sa.String(), nullable=True),
        sa.Column("difficulty", sa.String(), nullable=False, server_default="beginner"),
        sa.Column("order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("icon", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_lesson_modules_slug", "lesson_modules", ["slug"])

    # ---- lessons ----
    op.create_table(
        "lessons",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("module_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lesson_modules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slug", sa.String(), unique=True, nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("learning_objectives", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("task_type", sa.String(), nullable=False, server_default="action"),
        sa.Column("task_prompt", sa.Text(), nullable=False),
        sa.Column("task_hints", postgresql.JSONB(), nullable=True),
        sa.Column("verification_type", sa.String(), nullable=False, server_default="self_report"),
        sa.Column("token_reward", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column("generated_by_run_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("task_type IN ('action', 'reflection', 'quiz', 'exploration')", name="ck_lesson_task_type"),
        sa.CheckConstraint("verification_type IN ('self_report', 'ai_review')", name="ck_lesson_verification_type"),
        sa.CheckConstraint("status IN ('draft', 'published', 'archived')", name="ck_lesson_status"),
    )
    op.create_index("ix_lessons_slug", "lessons", ["slug"])
    op.create_index("ix_lessons_module_id", "lessons", ["module_id"])

    # ---- user_lesson_progress ----
    op.create_table(
        "user_lesson_progress",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lesson_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="started"),
        sa.Column("task_response", sa.Text(), nullable=True),
        sa.Column("ai_feedback", sa.Text(), nullable=True),
        sa.Column("tokens_awarded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "lesson_id", name="uq_user_lesson"),
    )
    op.create_index("ix_user_lesson_progress_user_id", "user_lesson_progress", ["user_id"])
    op.create_index("ix_user_lesson_progress_lesson_id", "user_lesson_progress", ["lesson_id"])

    # ---- user_tokens ----
    op.create_table(
        "user_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("balance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_earned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("longest_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_user_tokens_user_id", "user_tokens", ["user_id"])

    # ---- token_transactions ----
    op.create_table(
        "token_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("transaction_type", sa.String(), nullable=False),
        sa.Column("reference_id", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_token_transactions_user_id", "token_transactions", ["user_id"])

    # ---- Seed modules ----
    modules_tbl = sa.table(
        "lesson_modules",
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("sector", sa.String),
        sa.column("difficulty", sa.String),
        sa.column("order", sa.Integer),
        sa.column("icon", sa.String),
    )

    op.bulk_insert(modules_tbl, [
        {
            "slug": "ai-foundations",
            "name": "AI Foundations",
            "description": "Build your baseline understanding of AI \u2014 what it is, how to use it, and how to evaluate it critically.",
            "sector": None,
            "difficulty": "beginner",
            "order": 1,
            "icon": "academic-cap",
        },
        {
            "slug": "responsible-ai-use",
            "name": "Responsible AI Use",
            "description": "Develop the policies, habits, and critical frameworks needed to use AI ethically in your organisation.",
            "sector": None,
            "difficulty": "beginner",
            "order": 2,
            "icon": "shield-check",
        },
    ])

    # ---- Seed lessons ----
    conn = op.get_bind()
    module1_id = conn.execute(sa.text("SELECT id FROM lesson_modules WHERE slug = 'ai-foundations'")).scalar()
    module2_id = conn.execute(sa.text("SELECT id FROM lesson_modules WHERE slug = 'responsible-ai-use'")).scalar()

    lessons_tbl = sa.table(
        "lessons",
        sa.column("module_id", postgresql.UUID),
        sa.column("slug", sa.String),
        sa.column("title", sa.String),
        sa.column("description", sa.Text),
        sa.column("content_markdown", sa.Text),
        sa.column("learning_objectives", postgresql.JSONB),
        sa.column("task_type", sa.String),
        sa.column("task_prompt", sa.Text),
        sa.column("task_hints", postgresql.JSONB),
        sa.column("verification_type", sa.String),
        sa.column("token_reward", sa.Integer),
        sa.column("order", sa.Integer),
        sa.column("estimated_minutes", sa.Integer),
        sa.column("status", sa.String),
    )

    op.bulk_insert(lessons_tbl, [
        # ---- Module 1: AI Foundations ----
        {
            "module_id": module1_id,
            "slug": "ai-foundations-what-is-ai",
            "title": "What is AI?",
            "description": "Demystify artificial intelligence before you start using it.",
            "content_markdown": (
                "## What is AI?\n\n"
                "Artificial intelligence (AI) refers to systems that can perform tasks that "
                "typically require human intelligence \u2014 such as understanding language, "
                "recognising images, or making recommendations.\n\n"
                "**Types you'll encounter:**\n"
                "- **Generative AI** (e.g. ChatGPT, Claude) \u2014 creates text, images, code\n"
                "- **Classification AI** \u2014 labels and categorises data\n"
                "- **Recommendation AI** \u2014 suggests content based on patterns\n\n"
                "AI is not magic. It is pattern-matching at scale, trained on large datasets. "
                "It can be wrong, biased, or confidently incorrect."
            ),
            "learning_objectives": ["Explain AI in plain language", "Distinguish generative AI from other AI types", "Identify one AI limitation"],
            "task_type": "reflection",
            "task_prompt": "In two or three sentences, describe AI to a colleague who has never used it before. What would you say?",
            "task_hints": ["Focus on what AI does rather than how it works", "Use an analogy if that helps"],
            "verification_type": "self_report",
            "token_reward": 1,
            "order": 1,
            "estimated_minutes": 5,
            "status": "published",
        },
        {
            "module_id": module1_id,
            "slug": "ai-foundations-try-a-chatbot",
            "title": "Try a Chatbot",
            "description": "Get hands-on: have your first meaningful conversation with an AI assistant.",
            "content_markdown": (
                "## Try a Chatbot\n\n"
                "Reading about AI is one thing. Using it is another. In this lesson you will "
                "have a real conversation with an AI assistant to see what it can and cannot do.\n\n"
                "**Suggested starting points:**\n"
                "- Ask it to explain a complex topic in simple terms\n"
                "- Ask it to summarise a document you paste in\n"
                "- Ask it something factual and then verify the answer\n\n"
                "**Free tools to try:**\n"
                "- [ChatGPT](https://chat.openai.com) (OpenAI)\n"
                "- [Claude](https://claude.ai) (Anthropic)\n"
                "- [Gemini](https://gemini.google.com) (Google)"
            ),
            "learning_objectives": ["Complete a task using a chatbot", "Note at least one surprising strength", "Note at least one clear limitation"],
            "task_type": "action",
            "task_prompt": "Have a conversation with any AI chatbot. Try at least two different types of request. Then tick the box below to confirm you have completed this.",
            "task_hints": None,
            "verification_type": "self_report",
            "token_reward": 1,
            "order": 2,
            "estimated_minutes": 10,
            "status": "published",
        },
        {
            "module_id": module1_id,
            "slug": "ai-foundations-personalise-ai",
            "title": "Personalise Your AI Assistant",
            "description": "Make ChatGPT more useful by giving it context about who you are and what you need.",
            "content_markdown": (
                "## Personalise Your AI Assistant\n\n"
                "ChatGPT has a 'Custom Instructions' feature that lets you tell it about "
                "yourself and how you want it to respond \u2014 once, without repeating yourself "
                "every conversation.\n\n"
                "**To set custom instructions in ChatGPT:**\n"
                "1. Click your profile icon (bottom-left)\n"
                "2. Select **Customize ChatGPT**\n"
                "3. Fill in 'What would you like ChatGPT to know about you?'\n"
                "4. Fill in 'How would you like ChatGPT to respond?'\n\n"
                "**What to include:**\n"
                "- Your role and sector\n"
                "- Your AI experience level\n"
                "- Your preferred response style (concise vs detailed, formal vs conversational)\n"
                "- Any topics you regularly work on"
            ),
            "learning_objectives": ["Configure custom instructions in ChatGPT", "Articulate your personal AI context", "Test the improvement in response relevance"],
            "task_type": "action",
            "task_prompt": "Set up Custom Instructions in ChatGPT (or equivalent personalisation in another AI tool). Then describe what you wrote in the 'about you' section \u2014 what did you include, and why?",
            "task_hints": ["Focus on your work context, not personal details", "Mention your sector and the kinds of tasks you do most"],
            "verification_type": "ai_review",
            "token_reward": 2,
            "order": 3,
            "estimated_minutes": 10,
            "status": "published",
        },
        {
            "module_id": module1_id,
            "slug": "ai-foundations-evaluate-output",
            "title": "Evaluate AI Output",
            "description": "Learn the critical habit of checking what AI produces before you use it.",
            "content_markdown": (
                "## Evaluate AI Output\n\n"
                "AI systems make mistakes. They can produce plausible-sounding but incorrect "
                "information \u2014 sometimes called 'hallucinations'. Developing a habit of critical "
                "evaluation is one of the most important AI skills you can build.\n\n"
                "**A simple evaluation checklist:**\n"
                "1. **Verify facts** \u2014 Can you confirm key claims from another source?\n"
                "2. **Check for bias** \u2014 Does the response skew towards a particular viewpoint?\n"
                "3. **Assess completeness** \u2014 Is anything obviously missing?\n"
                "4. **Check tone** \u2014 Is the style appropriate for your context?\n"
                "5. **Review for hallucinations** \u2014 Are there specific names, dates, or URLs that seem questionable?"
            ),
            "learning_objectives": ["Apply a structured evaluation framework to AI output", "Identify at least one error or limitation in an AI response", "Explain why verification matters"],
            "task_type": "reflection",
            "task_prompt": "Ask an AI assistant a question related to your work. Then critically evaluate the response using the checklist above. What did you find? What would you trust, and what would you verify?",
            "task_hints": ["Choose a topic where you have some existing knowledge", "Be specific \u2014 vague responses are harder to evaluate"],
            "verification_type": "ai_review",
            "token_reward": 2,
            "order": 4,
            "estimated_minutes": 15,
            "status": "published",
        },
        # ---- Module 2: Responsible AI Use ----
        {
            "module_id": module2_id,
            "slug": "responsible-ai-bias-and-fairness",
            "title": "AI Bias and Fairness",
            "description": "Understand why AI systems can be biased and what that means for your organisation.",
            "content_markdown": (
                "## AI Bias and Fairness\n\n"
                "AI systems learn from data created by humans \u2014 which means they can inherit "
                "and amplify existing biases. This is not a theoretical problem: it has real "
                "consequences for hiring, lending, healthcare, and journalism.\n\n"
                "**Common sources of bias:**\n"
                "- **Training data bias** \u2014 if the data over-represents certain groups, the model will too\n"
                "- **Label bias** \u2014 human labellers bring their own assumptions\n"
                "- **Feedback loops** \u2014 models optimised for engagement can amplify divisive content\n\n"
                "**What to watch for in your work:**\n"
                "- AI tools that produce stereotyped outputs\n"
                "- Recommendations that consistently exclude certain groups\n"
                "- Translation or summarisation that loses cultural nuance"
            ),
            "learning_objectives": ["Identify at least two sources of AI bias", "Apply a bias lens to one AI tool you use", "Articulate why bias matters in your context"],
            "task_type": "reflection",
            "task_prompt": "Think about an AI tool you use or are considering using. Where could bias show up in its outputs? What would you look for to detect it?",
            "task_hints": None,
            "verification_type": "self_report",
            "token_reward": 1,
            "order": 1,
            "estimated_minutes": 8,
            "status": "published",
        },
        {
            "module_id": module2_id,
            "slug": "responsible-ai-write-use-policy",
            "title": "Write an AI Use Policy",
            "description": "Draft a practical AI use policy for your organisation or team.",
            "content_markdown": (
                "## Write an AI Use Policy\n\n"
                "An AI use policy sets clear expectations for how your organisation uses AI \u2014 "
                "what is allowed, what requires approval, and what is prohibited.\n\n"
                "**A minimal policy covers:**\n"
                "1. **Permitted uses** \u2014 tasks where AI is encouraged (e.g. drafting, research support)\n"
                "2. **Restricted uses** \u2014 tasks requiring human review before AI output is used\n"
                "3. **Prohibited uses** \u2014 tasks where AI must not be used (e.g. final decisions on individuals)\n"
                "4. **Disclosure** \u2014 when and how to disclose AI use to audiences or clients\n"
                "5. **Data** \u2014 what information must not be shared with AI tools\n\n"
                "You can also use Grounded's **Policy Builder** to create a full structured policy."
            ),
            "learning_objectives": ["Draft at least three policy rules for your context", "Distinguish permitted, restricted, and prohibited AI uses", "Consider disclosure requirements"],
            "task_type": "action",
            "task_prompt": "Draft a short AI use policy for your organisation or team. Include at least: one permitted use, one restricted use, one prohibited use, and a disclosure statement. Share your draft below.",
            "task_hints": ["Start with the tasks your team already uses AI for", "Think about your audience's trust and your accountability obligations"],
            "verification_type": "ai_review",
            "token_reward": 2,
            "order": 2,
            "estimated_minutes": 20,
            "status": "published",
        },
        {
            "module_id": module2_id,
            "slug": "responsible-ai-data-privacy",
            "title": "Data Privacy with AI",
            "description": "Understand the data risks of using AI tools and how to protect sensitive information.",
            "content_markdown": (
                "## Data Privacy with AI\n\n"
                "When you paste text into a commercial AI tool, that data may be used to train "
                "future models unless you opt out or use an enterprise tier. This creates real "
                "privacy risks \u2014 especially for organisations handling sensitive data.\n\n"
                "**Key rules of thumb:**\n"
                "- Never paste personally identifiable information (PII) into consumer AI tools\n"
                "- Do not share confidential source details, client data, or financial records\n"
                "- Check whether your AI tool is GDPR-compliant for your region\n"
                "- Prefer tools that offer data processing agreements (DPAs)\n\n"
                "**For higher-risk use cases:**\n"
                "- Use enterprise tiers with data isolation guarantees\n"
                "- Consider self-hosted or on-premise AI solutions\n"
                "- Build anonymisation steps into your workflow before using AI"
            ),
            "learning_objectives": ["Identify what data is safe to share with AI tools", "Know the difference between consumer and enterprise AI data policies", "Apply a data review step before using AI"],
            "task_type": "exploration",
            "task_prompt": "Review the privacy policy of one AI tool you use. What does it say about data retention and training use? Share what you found \u2014 even if it was hard to locate.",
            "task_hints": ["Look for terms like 'training data', 'data retention', 'opt-out'", "The privacy policy is usually linked in the footer"],
            "verification_type": "self_report",
            "token_reward": 1,
            "order": 3,
            "estimated_minutes": 10,
            "status": "published",
        },
        {
            "module_id": module2_id,
            "slug": "responsible-ai-transparency-checklist",
            "title": "AI Transparency Checklist",
            "description": "Build a reusable checklist for being transparent about AI use in your outputs.",
            "content_markdown": (
                "## AI Transparency Checklist\n\n"
                "Transparency about AI use is becoming a professional and regulatory expectation "
                "in journalism, legal practice, NGO work, and business communications.\n\n"
                "**What transparency requires:**\n"
                "- Disclosing when AI was used to generate or substantially assist with content\n"
                "- Explaining how AI output was verified before publication or submission\n"
                "- Noting any known limitations of the AI tool used\n"
                "- Storing records of AI use for accountability purposes\n\n"
                "**Different contexts, different standards:**\n"
                "- **Journalism**: Many outlets require disclosure in bylines or editor's notes\n"
                "- **Legal**: Some jurisdictions require disclosure of AI use in filings\n"
                "- **NGO reporting**: Funders may require disclosure in reports"
            ),
            "learning_objectives": ["Create a reusable AI transparency checklist", "Identify the disclosure standards relevant to your context", "Apply transparency thinking to a real piece of work"],
            "task_type": "action",
            "task_prompt": "Create an AI transparency checklist for your organisation. It should cover: when to disclose AI use, how to document it, and who is responsible for verification. Share your checklist below.",
            "task_hints": ["Tailor it to your sector's existing standards", "Make it short enough to actually use \u2014 no more than 8 items"],
            "verification_type": "ai_review",
            "token_reward": 2,
            "order": 4,
            "estimated_minutes": 15,
            "status": "published",
        },
    ])


def downgrade():
    op.drop_table("token_transactions")
    op.drop_table("user_tokens")
    op.drop_table("user_lesson_progress")
    op.drop_table("lessons")
    op.drop_table("lesson_modules")
