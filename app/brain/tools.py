"""Tool definitions for the Grounded Brain.

Each tool is defined as an Anthropic tool schema dict + an executor function.
The Brain engine calls these during its tool_use loop.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.models.directory import MediaOrganization
from app.models.discovery import DiscoveredTool
from app.models.usecase import UseCase
from app.models.governance import ContentItem

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Execution context (passed to every tool executor)
# ---------------------------------------------------------------------------

@dataclass
class BrainContext:
    """Context passed to tool executors during a Brain run."""
    db: Session
    run_id: str
    created_records: list[dict] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    steps_taken: int = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugify(text: str) -> str:
    """Create a URL-friendly slug from text."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text[:200]


def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    url = url.lower().strip()
    for prefix in ("https://", "http://", "www."):
        if url.startswith(prefix):
            url = url[len(prefix):]
    return url.split("/")[0]


# ---------------------------------------------------------------------------
# Tool schema definitions (Anthropic format)
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "search_existing_records",
        "description": (
            "Search for existing records in the database to check for duplicates "
            "before creating new ones. Always call this before creating a record."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "record_type": {
                    "type": "string",
                    "description": "Type of record to search. Must be 'organization', 'tool', 'use_case', or 'content'.",
                    "enum": ["organization", "tool", "use_case", "content"],
                },
                "query": {
                    "type": "string",
                    "description": "Search query matched against name/title via case-insensitive contains.",
                },
            },
            "required": ["record_type", "query"],
        },
    },
    {
        "name": "create_media_organization",
        "description": (
            "Create a new media organization record in draft status. "
            "Always use search_existing_records first to avoid duplicates."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Organization name."},
                "org_type": {
                    "type": "string",
                    "description": "Type of organization.",
                    "enum": ["newspaper", "broadcaster", "digital", "agency", "freelance_collective"],
                },
                "website": {"type": "string", "description": "Organization website URL."},
                "country": {"type": "string", "description": "Country of operation."},
                "description": {"type": "string", "description": "Brief description of the organization."},
                "notes": {"type": "string", "description": "Additional context (ownership, coverage areas)."},
            },
            "required": ["name", "org_type"],
        },
    },
    {
        "name": "create_discovered_tool",
        "description": (
            "Create a new AI tool record in pending_review status. "
            "Always use search_existing_records first to avoid duplicates."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Tool name."},
                "url": {"type": "string", "description": "Tool website URL."},
                "description": {"type": "string", "description": "What the tool does."},
                "category": {
                    "type": "string",
                    "description": "Primary category (e.g. 'fact-checking', 'transcription', 'content-generation').",
                },
                "pricing_model": {
                    "type": "string",
                    "description": "Pricing model.",
                    "enum": ["free", "freemium", "paid", "open_source", "enterprise"],
                },
            },
            "required": ["name", "url", "description"],
        },
    },
    {
        "name": "create_use_case",
        "description": (
            "Create a new AI use case record in pending_review status. "
            "Always use search_existing_records first to avoid duplicates."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title (e.g. 'BBC Uses AI for Election Coverage Verification').",
                },
                "organization": {"type": "string", "description": "Name of the implementing organization."},
                "summary": {"type": "string", "description": "Brief overview (2-3 sentences)."},
                "challenge": {"type": "string", "description": "Problem the organization faced."},
                "solution": {"type": "string", "description": "AI solution implemented."},
                "outcome": {"type": "string", "description": "Results and impact."},
                "lessons_learned": {"type": "string", "description": "Key takeaways."},
                "country": {"type": "string", "description": "Country of operation."},
                "region": {"type": "string", "description": "Geographic region."},
                "organization_type": {
                    "type": "string",
                    "description": "Type of organization.",
                    "enum": ["newspaper", "broadcaster", "digital native", "agency", "ngo", "law_firm", "business"],
                },
                "source_url": {"type": "string", "description": "URL of the original article or case study."},
                "source_name": {"type": "string", "description": "Name of the source."},
                "tools_mentioned": {
                    "type": "string",
                    "description": "Comma-separated list of AI tools mentioned.",
                },
            },
            "required": ["title", "organization", "summary"],
        },
    },
    {
        "name": "create_legal_framework_content",
        "description": (
            "Create a legal framework content item in pending_review status. "
            "Always use search_existing_records first to avoid duplicates."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title (e.g. 'EU AI Act: Key Requirements for Organisations').",
                },
                "content_markdown": {
                    "type": "string",
                    "description": "Full markdown content describing the framework and its implications.",
                },
                "summary": {"type": "string", "description": "Brief summary (2-3 sentences)."},
                "jurisdiction": {
                    "type": "string",
                    "description": "Applicable jurisdiction (e.g. 'eu', 'uk', 'us_federal', 'global').",
                },
                "source_url": {"type": "string", "description": "URL of the official regulation."},
            },
            "required": ["title", "content_markdown"],
        },
    },
    {
        "name": "search_existing_lessons",
        "description": (
            "Search for existing lessons to avoid duplicates before creating new ones."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search text matched against lesson title.",
                },
                "module_slug": {
                    "type": "string",
                    "description": "Optional: limit search to a specific module by slug.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "create_lesson",
        "description": (
            "Create a new lesson record in a specified module with status='draft'. "
            "Always use search_existing_lessons first to avoid duplicates."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "module_slug": {
                    "type": "string",
                    "description": "Slug of the target module (e.g. 'ai-foundations').",
                },
                "title": {"type": "string", "description": "Lesson title."},
                "description": {"type": "string", "description": "One-sentence summary."},
                "content_markdown": {
                    "type": "string",
                    "description": "Full teaching content in markdown. Minimum 200 characters.",
                },
                "learning_objectives": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "2-4 specific learning outcomes.",
                },
                "task_type": {
                    "type": "string",
                    "enum": ["action", "reflection", "quiz", "exploration"],
                    "description": "Type of practical task.",
                },
                "task_prompt": {
                    "type": "string",
                    "description": "Clear instruction for what the user must do.",
                },
                "task_hints": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional 1-3 hints to help users complete the task.",
                },
                "verification_type": {
                    "type": "string",
                    "enum": ["self_report", "ai_review"],
                    "description": "self_report for actions, ai_review for written responses.",
                },
                "token_reward": {
                    "type": "integer",
                    "description": "Tokens awarded on completion. Use 1 for self_report, 2 for ai_review.",
                },
                "estimated_minutes": {
                    "type": "integer",
                    "description": "Estimated completion time in minutes.",
                },
            },
            "required": ["module_slug", "title", "content_markdown", "task_type", "task_prompt", "verification_type"],
        },
    },
    {
        "name": "create_ethics_policy_content",
        "description": (
            "Create an ethics policy content item in pending_review status. "
            "Always use search_existing_records first to avoid duplicates."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title (e.g. 'Associated Press AI Ethics Guidelines').",
                },
                "content_markdown": {
                    "type": "string",
                    "description": "Full markdown content describing the policy and its provisions.",
                },
                "summary": {"type": "string", "description": "Brief summary (2-3 sentences)."},
                "source_url": {"type": "string", "description": "URL of the original policy document."},
                "source_name": {"type": "string", "description": "Organization that published the policy."},
            },
            "required": ["title", "content_markdown"],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool executor functions
# ---------------------------------------------------------------------------

def execute_search_existing_records(ctx: BrainContext, record_type: str, query: str) -> str:
    """Search for existing records to check for duplicates."""
    db = ctx.db
    ctx.steps_taken += 1

    if not query.strip():
        return "Error: query parameter is required."

    results = []

    if record_type == "organization":
        matches = (
            db.query(MediaOrganization)
            .filter(MediaOrganization.name.ilike(f"%{query}%"))
            .limit(10)
            .all()
        )
        for m in matches:
            results.append(f"- {m.name} (type={m.org_type}, country={m.country}, id={m.id})")

    elif record_type == "tool":
        matches = (
            db.query(DiscoveredTool)
            .filter(DiscoveredTool.name.ilike(f"%{query}%"))
            .limit(10)
            .all()
        )
        for m in matches:
            results.append(f"- {m.name} (status={m.status}, url={m.url}, id={m.id})")

    elif record_type == "use_case":
        matches = (
            db.query(UseCase)
            .filter(UseCase.title.ilike(f"%{query}%"))
            .limit(10)
            .all()
        )
        for m in matches:
            results.append(f"- {m.title} (org={m.organization}, status={m.status}, id={m.id})")

    elif record_type == "content":
        matches = (
            db.query(ContentItem)
            .filter(ContentItem.title.ilike(f"%{query}%"))
            .limit(10)
            .all()
        )
        for m in matches:
            results.append(f"- {m.title} (section={m.section}, status={m.status}, id={m.id})")

    else:
        return f"Error: unknown record_type '{record_type}'. Use 'organization', 'tool', 'use_case', or 'content'."

    if not results:
        return f"No existing {record_type} records found matching '{query}'."

    return f"Found {len(results)} existing {record_type} record(s):\n" + "\n".join(results)


def execute_create_media_organization(ctx: BrainContext, **kwargs: Any) -> str:
    """Create a new media organization record in draft status."""
    db = ctx.db
    run_id = ctx.run_id
    ctx.steps_taken += 1

    name = kwargs.get("name", "").strip()
    if not name:
        return "Error: name is required."

    existing = (
        db.query(MediaOrganization)
        .filter(MediaOrganization.name.ilike(name))
        .first()
    )
    if existing:
        return f"Duplicate: organization '{existing.name}' already exists (id={existing.id}). Skipped."

    org = MediaOrganization(
        name=name,
        org_type=kwargs.get("org_type", "digital"),
        website=kwargs.get("website") or None,
        country=kwargs.get("country") or None,
        description=kwargs.get("description") or None,
        notes=(kwargs.get("notes") or "") + f"\n[source=brain, run_id={run_id}]",
        is_active=False,
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    ctx.created_records.append({
        "tool": "create_media_organization",
        "record_type": "organization",
        "record_id": str(org.id),
        "name": name,
        "output": f"Created organization '{org.name}' (id={org.id})",
    })

    logger.info(f"Brain created MediaOrganization: {org.name} (id={org.id})")
    return f"Created organization '{org.name}' (id={org.id}) in draft status."


def execute_create_discovered_tool(ctx: BrainContext, **kwargs: Any) -> str:
    """Create a new discovered tool record in pending_review status."""
    db = ctx.db
    run_id = ctx.run_id
    ctx.steps_taken += 1

    name = kwargs.get("name", "").strip()
    url = kwargs.get("url", "").strip()
    if not name or not url:
        return "Error: name and url are required."

    slug = _slugify(name)
    domain = _extract_domain(url)

    existing = (
        db.query(DiscoveredTool)
        .filter(
            (DiscoveredTool.slug == slug) | (DiscoveredTool.url_domain == domain)
        )
        .first()
    )
    if existing:
        return f"Duplicate: tool '{existing.name}' already exists (url={existing.url}, id={existing.id}). Skipped."

    category = kwargs.get("category", "")
    tool = DiscoveredTool(
        name=name,
        slug=slug,
        url=url,
        url_domain=domain,
        description=kwargs.get("description") or None,
        categories=([category] if category else []),
        tags=[],
        source_type="agent",
        source_url="agent",
        source_name=f"Grounded Brain (run {run_id})",
        status="pending_review",
        confidence_score=0.7,
        extra_data={
            "pricing_model": kwargs.get("pricing_model") or None,
            "brain_run_id": run_id,
        },
    )
    db.add(tool)
    db.commit()
    db.refresh(tool)

    ctx.created_records.append({
        "tool": "create_discovered_tool",
        "record_type": "tool",
        "record_id": str(tool.id),
        "name": name,
        "output": f"Created tool '{tool.name}' (id={tool.id})",
    })

    logger.info(f"Brain created DiscoveredTool: {tool.name} (id={tool.id})")
    return f"Created tool '{tool.name}' (id={tool.id}) in pending_review status."


def execute_create_use_case(ctx: BrainContext, **kwargs: Any) -> str:
    """Create a new use case record in pending_review status."""
    db = ctx.db
    run_id = ctx.run_id
    ctx.steps_taken += 1

    title = kwargs.get("title", "").strip()
    organization = kwargs.get("organization", "").strip()
    if not title or not organization:
        return "Error: title and organization are required."

    slug = _slugify(title)

    existing = db.query(UseCase).filter(UseCase.slug == slug).first()
    if existing:
        return f"Duplicate: use case '{existing.title}' already exists (id={existing.id}). Skipped."

    tools_mentioned = kwargs.get("tools_mentioned", "")
    tools_list = [t.strip() for t in tools_mentioned.split(",") if t.strip()] if tools_mentioned else []

    use_case = UseCase(
        title=title,
        slug=slug,
        organization=organization or None,
        country=kwargs.get("country") or None,
        region=kwargs.get("region") or None,
        organization_type=kwargs.get("organization_type") or None,
        summary=kwargs.get("summary") or None,
        challenge=kwargs.get("challenge") or None,
        solution=kwargs.get("solution") or None,
        outcome=kwargs.get("outcome") or None,
        lessons_learned=kwargs.get("lessons_learned") or None,
        tools_mentioned=tools_list,
        source_url=kwargs.get("source_url") or None,
        source_name=kwargs.get("source_name") or f"Grounded Brain (run {run_id})",
        source_type="manual",
        status="pending_review",
        confidence_score=0.7,
    )
    db.add(use_case)
    db.commit()
    db.refresh(use_case)

    ctx.created_records.append({
        "tool": "create_use_case",
        "record_type": "use_case",
        "record_id": str(use_case.id),
        "name": title,
        "output": f"Created use case '{use_case.title}' (id={use_case.id})",
    })

    logger.info(f"Brain created UseCase: {use_case.title} (id={use_case.id})")
    return f"Created use case '{use_case.title}' (id={use_case.id}) in pending_review status."


def execute_create_legal_framework_content(ctx: BrainContext, **kwargs: Any) -> str:
    """Create a legal framework content item in pending_review status."""
    db = ctx.db
    run_id = ctx.run_id
    ctx.steps_taken += 1

    title = kwargs.get("title", "").strip()
    content_markdown = kwargs.get("content_markdown", "").strip()
    if not title or not content_markdown:
        return "Error: title and content_markdown are required."

    slug = _slugify(title)

    existing = db.query(ContentItem).filter(ContentItem.slug == slug).first()
    if existing:
        return f"Duplicate: content '{existing.title}' already exists (id={existing.id}). Skipped."

    summary = kwargs.get("summary", "")
    source_url = kwargs.get("source_url", "")

    item = ContentItem(
        title=title,
        slug=slug,
        content_markdown=content_markdown,
        summary=summary or None,
        excerpt=summary[:200] if summary else None,
        content_type="framework_summary",
        section="legal_framework",
        jurisdiction=kwargs.get("jurisdiction") or None,
        tags=["brain-generated"],
        sources=[{"url": source_url, "title": title, "brain_run_id": run_id}] if source_url else [],
        status="pending_review",
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    ctx.created_records.append({
        "tool": "create_legal_framework_content",
        "record_type": "content",
        "record_id": str(item.id),
        "name": title,
        "output": f"Created legal framework content '{item.title}' (id={item.id})",
    })

    logger.info(f"Brain created legal ContentItem: {item.title} (id={item.id})")
    return f"Created legal framework content '{item.title}' (id={item.id}) in pending_review status."


def execute_create_ethics_policy_content(ctx: BrainContext, **kwargs: Any) -> str:
    """Create an ethics policy content item in pending_review status."""
    db = ctx.db
    run_id = ctx.run_id
    ctx.steps_taken += 1

    title = kwargs.get("title", "").strip()
    content_markdown = kwargs.get("content_markdown", "").strip()
    if not title or not content_markdown:
        return "Error: title and content_markdown are required."

    slug = _slugify(title)

    existing = db.query(ContentItem).filter(ContentItem.slug == slug).first()
    if existing:
        return f"Duplicate: content '{existing.title}' already exists (id={existing.id}). Skipped."

    summary = kwargs.get("summary", "")
    source_url = kwargs.get("source_url", "")
    source_name = kwargs.get("source_name", "")

    item = ContentItem(
        title=title,
        slug=slug,
        content_markdown=content_markdown,
        summary=summary or None,
        excerpt=summary[:200] if summary else None,
        content_type="policy",
        section="ethics_policy",
        tags=["brain-generated"],
        sources=[{"url": source_url, "title": source_name or title, "brain_run_id": run_id}] if source_url else [],
        status="pending_review",
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    ctx.created_records.append({
        "tool": "create_ethics_policy_content",
        "record_type": "content",
        "record_id": str(item.id),
        "name": title,
        "output": f"Created ethics policy content '{item.title}' (id={item.id})",
    })

    logger.info(f"Brain created ethics ContentItem: {item.title} (id={item.id})")
    return f"Created ethics policy content '{item.title}' (id={item.id}) in pending_review status."


def execute_search_existing_lessons(ctx: BrainContext, query: str, module_slug: str = "") -> str:
    """Search for existing lessons to check for duplicates."""
    from app.models.lessons import Lesson, LessonModule

    db = ctx.db
    ctx.steps_taken += 1

    q = db.query(Lesson).filter(Lesson.title.ilike(f"%{query}%"))
    if module_slug:
        module = db.query(LessonModule).filter(LessonModule.slug == module_slug).first()
        if module:
            q = q.filter(Lesson.module_id == module.id)

    matches = q.limit(10).all()
    if not matches:
        return f"No existing lessons found matching '{query}'."

    results = [f"- {l.title} (status={l.status}, slug={l.slug}, id={l.id})" for l in matches]
    return f"Found {len(matches)} lesson(s):\n" + "\n".join(results)


def execute_create_lesson(ctx: BrainContext, **kwargs: Any) -> str:
    """Create a new lesson in draft status."""
    from app.models.lessons import LessonModule, Lesson
    from sqlalchemy import func as sa_func

    db = ctx.db
    run_id = ctx.run_id
    ctx.steps_taken += 1

    module_slug = kwargs.get("module_slug", "").strip()
    title = kwargs.get("title", "").strip()
    content_markdown = kwargs.get("content_markdown", "").strip()

    if not module_slug or not title or not content_markdown:
        return "Error: module_slug, title, and content_markdown are required."

    # Find module
    module = db.query(LessonModule).filter(LessonModule.slug == module_slug).first()
    if not module:
        return f"Error: module '{module_slug}' not found."

    # Generate slug
    slug = _slugify(title)
    if not slug:
        return "Error: could not generate a slug from the title."

    # Check for duplicate
    existing = db.query(Lesson).filter(Lesson.slug == slug).first()
    if existing:
        return f"Duplicate: lesson '{existing.title}' already exists (slug={slug}). Skipped."

    # Determine order (next after existing lessons in this module)
    max_order = db.query(sa_func.max(Lesson.order)).filter(Lesson.module_id == module.id).scalar() or 0

    lesson = Lesson(
        module_id=module.id,
        slug=slug,
        title=title,
        description=kwargs.get("description") or None,
        content_markdown=content_markdown,
        learning_objectives=kwargs.get("learning_objectives") or [],
        task_type=kwargs.get("task_type", "action"),
        task_prompt=kwargs.get("task_prompt", ""),
        task_hints=kwargs.get("task_hints") or None,
        verification_type=kwargs.get("verification_type", "self_report"),
        token_reward=kwargs.get("token_reward", 1),
        order=max_order + 1,
        estimated_minutes=kwargs.get("estimated_minutes") or None,
        generated_by_run_id=run_id,
        status="draft",
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)

    ctx.created_records.append({
        "tool": "create_lesson",
        "record_type": "lesson",
        "record_id": str(lesson.id),
        "name": title,
        "output": f"Created lesson '{lesson.title}' in module '{module.name}' (id={lesson.id})",
    })

    logger.info(f"Brain created Lesson: {lesson.title} (id={lesson.id})")
    return f"Created lesson '{lesson.title}' in module '{module.slug}' (id={lesson.id}) as draft."


# ---------------------------------------------------------------------------
# Tool executor dispatch
# ---------------------------------------------------------------------------

TOOL_EXECUTORS = {
    "search_existing_records": execute_search_existing_records,
    "create_media_organization": execute_create_media_organization,
    "create_discovered_tool": execute_create_discovered_tool,
    "create_use_case": execute_create_use_case,
    "create_legal_framework_content": execute_create_legal_framework_content,
    "create_ethics_policy_content": execute_create_ethics_policy_content,
    "search_existing_lessons": execute_search_existing_lessons,
    "create_lesson": execute_create_lesson,
}


def execute_tool(ctx: BrainContext, tool_name: str, tool_input: dict[str, Any]) -> str:
    """Execute a tool by name with the given input.

    Args:
        ctx: Brain execution context
        tool_name: Name of the tool to execute
        tool_input: Tool input parameters

    Returns:
        Tool result as a string
    """
    executor = TOOL_EXECUTORS.get(tool_name)
    if not executor:
        return f"Error: unknown tool '{tool_name}'."

    try:
        if tool_name == "search_existing_records":
            return executor(ctx, record_type=tool_input["record_type"], query=tool_input["query"])
        elif tool_name == "search_existing_lessons":
            return executor(ctx, query=tool_input["query"], module_slug=tool_input.get("module_slug", ""))
        else:
            return executor(ctx, **tool_input)
    except Exception as e:
        logger.exception(f"Tool execution error: {tool_name}")
        return f"Error executing {tool_name}: {e}"


def get_tool_schemas(allowed_tools: list[str] | None = None) -> list[dict[str, Any]]:
    """Get tool schemas, optionally filtered by allowed tool names.

    Args:
        allowed_tools: If provided, only return schemas for these tools.
            If None, return all tool schemas.

    Returns:
        List of Anthropic tool schema dicts
    """
    if allowed_tools is None:
        return TOOL_SCHEMAS

    return [s for s in TOOL_SCHEMAS if s["name"] in allowed_tools]
