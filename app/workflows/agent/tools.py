"""Client-side tool definitions for the AI agent.

Uses the OpenAI Agents SDK @function_tool decorator to define
tools that the agent can call during its research loop.
"""
import re
import logging
from dataclasses import dataclass, field

from sqlalchemy.orm import Session
from agents import function_tool, RunContextWrapper

from app.models.directory import MediaOrganization
from app.models.discovery import DiscoveredTool
from app.models.usecase import UseCase
from app.models.governance import ContentItem

logger = logging.getLogger(__name__)


@dataclass
class AgentContext:
    """Context passed to agent tools during execution."""
    db: Session
    run_id: str
    created_records: list[dict] = field(default_factory=list)
    steps_taken: int = 0


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
# Tool definitions (using @function_tool decorator)
# ---------------------------------------------------------------------------

@function_tool
async def search_existing_records(
    ctx: RunContextWrapper[AgentContext],
    record_type: str,
    query: str,
) -> str:
    """Search for existing records in the database to check for duplicates before creating new ones.

    Args:
        record_type: Type of record to search for. Must be 'organization', 'tool', 'use_case', or 'content'.
        query: Search query matched against name/title via case-insensitive contains.
    """
    db = ctx.context.db
    ctx.context.steps_taken += 1

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


@function_tool
async def create_media_organization(
    ctx: RunContextWrapper[AgentContext],
    name: str,
    org_type: str,
    website: str = "",
    country: str = "",
    description: str = "",
    notes: str = "",
) -> str:
    """Create a new media organization record in draft status. Always use search_existing_records first to avoid duplicates.

    Args:
        name: Organization name.
        org_type: Type of media organization. One of: newspaper, broadcaster, digital, agency, freelance_collective.
        website: Organization website URL.
        country: Country of operation.
        description: Brief description of the organization.
        notes: Additional context such as ownership or coverage areas.
    """
    db = ctx.context.db
    run_id = ctx.context.run_id
    ctx.context.steps_taken += 1

    if not name.strip():
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
        org_type=org_type or "digital",
        website=website or None,
        country=country or None,
        description=description or None,
        notes=(notes or "") + f"\n[source=agent, run_id={run_id}]",
        is_active=False,  # Draft — not active until admin approves
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    ctx.context.created_records.append({
        "tool": "create_media_organization",
        "name": name,
        "output": f"Created organization '{org.name}' (id={org.id})",
    })

    logger.info(f"Agent created MediaOrganization: {org.name} (id={org.id})")
    return f"Created organization '{org.name}' (id={org.id}) in draft status."


@function_tool
async def create_discovered_tool(
    ctx: RunContextWrapper[AgentContext],
    name: str,
    url: str,
    description: str,
    category: str = "",
    pricing_model: str = "",
) -> str:
    """Create a new discovered tool record in pending_review status. Always use search_existing_records first to avoid duplicates.

    Args:
        name: Tool name.
        url: Tool website URL.
        description: What the tool does.
        category: Primary category such as fact-checking or transcription.
        pricing_model: Pricing model. One of: free, freemium, paid, open_source, enterprise.
    """
    db = ctx.context.db
    run_id = ctx.context.run_id
    ctx.context.steps_taken += 1

    if not name.strip() or not url.strip():
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

    tool = DiscoveredTool(
        name=name,
        slug=slug,
        url=url,
        url_domain=domain,
        description=description or None,
        categories=([category] if category else []),
        tags=[],
        source_type="agent",
        source_url="agent",
        source_name=f"AI Agent (run {run_id})",
        status="pending_review",
        confidence_score=0.7,
        extra_data={
            "pricing_model": pricing_model or None,
            "agent_run_id": run_id,
        },
    )
    db.add(tool)
    db.commit()
    db.refresh(tool)

    ctx.context.created_records.append({
        "tool": "create_discovered_tool",
        "name": name,
        "output": f"Created tool '{tool.name}' (id={tool.id})",
    })

    logger.info(f"Agent created DiscoveredTool: {tool.name} (id={tool.id})")
    return f"Created tool '{tool.name}' (id={tool.id}) in pending_review status."


@function_tool
async def create_use_case(
    ctx: RunContextWrapper[AgentContext],
    title: str,
    organization: str,
    summary: str,
    challenge: str = "",
    solution: str = "",
    outcome: str = "",
    lessons_learned: str = "",
    country: str = "",
    region: str = "",
    organization_type: str = "",
    source_url: str = "",
    source_name: str = "",
    tools_mentioned: str = "",
) -> str:
    """Create a new use case record in pending_review status. Always use search_existing_records first to avoid duplicates.

    Args:
        title: Title of the use case (e.g. 'BBC Uses AI for Election Coverage Verification').
        organization: Name of the news organization implementing the use case.
        summary: Brief overview of the use case (2-3 sentences).
        challenge: What problem the organization faced.
        solution: What AI solution they implemented.
        outcome: Results and impact of the implementation.
        lessons_learned: Key takeaways from the implementation.
        country: Country where the organization operates.
        region: Geographic region (e.g. 'Europe', 'North America').
        organization_type: Type of organization. One of: newspaper, broadcaster, digital native, agency, ngo.
        source_url: URL of the original article or case study.
        source_name: Name of the source (e.g. 'JournalismAI', 'Nieman Lab').
        tools_mentioned: Comma-separated list of AI tools mentioned in the use case.
    """
    db = ctx.context.db
    run_id = ctx.context.run_id
    ctx.context.steps_taken += 1

    if not title.strip() or not organization.strip():
        return "Error: title and organization are required."

    slug = _slugify(title)

    existing = db.query(UseCase).filter(UseCase.slug == slug).first()
    if existing:
        return f"Duplicate: use case '{existing.title}' already exists (id={existing.id}). Skipped."

    tools_list = [t.strip() for t in tools_mentioned.split(",") if t.strip()] if tools_mentioned else []

    use_case = UseCase(
        title=title,
        slug=slug,
        organization=organization or None,
        country=country or None,
        region=region or None,
        organization_type=organization_type or None,
        summary=summary or None,
        challenge=challenge or None,
        solution=solution or None,
        outcome=outcome or None,
        lessons_learned=lessons_learned or None,
        tools_mentioned=tools_list,
        source_url=source_url or None,
        source_name=source_name or f"AI Agent (run {run_id})",
        source_type="manual",
        status="pending_review",
        confidence_score=0.7,
    )
    db.add(use_case)
    db.commit()
    db.refresh(use_case)

    ctx.context.created_records.append({
        "tool": "create_use_case",
        "name": title,
        "output": f"Created use case '{use_case.title}' (id={use_case.id})",
    })

    logger.info(f"Agent created UseCase: {use_case.title} (id={use_case.id})")
    return f"Created use case '{use_case.title}' (id={use_case.id}) in pending_review status."


@function_tool
async def create_legal_framework_content(
    ctx: RunContextWrapper[AgentContext],
    title: str,
    content_markdown: str,
    summary: str = "",
    jurisdiction: str = "",
    source_url: str = "",
) -> str:
    """Create a legal framework content item in pending_review status for the governance section. Always use search_existing_records first to avoid duplicates.

    Args:
        title: Title of the legal framework or regulation (e.g. 'EU AI Act: Key Requirements for Media Organizations').
        content_markdown: Full markdown content describing the framework, its requirements, and implications for journalism.
        summary: Brief summary (2-3 sentences) of the framework.
        jurisdiction: Applicable jurisdiction (e.g. 'eu', 'uk', 'us_federal', 'global').
        source_url: URL of the official regulation or authoritative source.
    """
    db = ctx.context.db
    run_id = ctx.context.run_id
    ctx.context.steps_taken += 1

    if not title.strip() or not content_markdown.strip():
        return "Error: title and content_markdown are required."

    slug = _slugify(title)

    existing = db.query(ContentItem).filter(ContentItem.slug == slug).first()
    if existing:
        return f"Duplicate: content '{existing.title}' already exists (id={existing.id}). Skipped."

    item = ContentItem(
        title=title,
        slug=slug,
        content_markdown=content_markdown,
        summary=summary or None,
        excerpt=summary[:200] if summary else None,
        content_type="framework_summary",
        section="legal_framework",
        jurisdiction=jurisdiction or None,
        tags=["agent-generated"],
        sources=[{"url": source_url, "title": title, "agent_run_id": run_id}] if source_url else [],
        status="pending_review",
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    ctx.context.created_records.append({
        "tool": "create_legal_framework_content",
        "name": title,
        "output": f"Created legal framework content '{item.title}' (id={item.id})",
    })

    logger.info(f"Agent created legal ContentItem: {item.title} (id={item.id})")
    return f"Created legal framework content '{item.title}' (id={item.id}) in pending_review status. It will appear in Governance > Content for review."


@function_tool
async def create_ethics_policy_content(
    ctx: RunContextWrapper[AgentContext],
    title: str,
    content_markdown: str,
    summary: str = "",
    source_url: str = "",
    source_name: str = "",
) -> str:
    """Create an ethics policy content item in pending_review status for the governance section. Always use search_existing_records first to avoid duplicates.

    Args:
        title: Title of the ethics policy or guideline (e.g. 'Associated Press AI Ethics Guidelines').
        content_markdown: Full markdown content describing the policy, its principles, and key provisions.
        summary: Brief summary (2-3 sentences) of the policy.
        source_url: URL of the original policy document.
        source_name: Name of the organization that published the policy.
    """
    db = ctx.context.db
    run_id = ctx.context.run_id
    ctx.context.steps_taken += 1

    if not title.strip() or not content_markdown.strip():
        return "Error: title and content_markdown are required."

    slug = _slugify(title)

    existing = db.query(ContentItem).filter(ContentItem.slug == slug).first()
    if existing:
        return f"Duplicate: content '{existing.title}' already exists (id={existing.id}). Skipped."

    item = ContentItem(
        title=title,
        slug=slug,
        content_markdown=content_markdown,
        summary=summary or None,
        excerpt=summary[:200] if summary else None,
        content_type="policy",
        section="ethics_policy",
        tags=["agent-generated"],
        sources=[{"url": source_url, "title": source_name or title, "agent_run_id": run_id}] if source_url else [],
        status="pending_review",
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    ctx.context.created_records.append({
        "tool": "create_ethics_policy_content",
        "name": title,
        "output": f"Created ethics policy content '{item.title}' (id={item.id})",
    })

    logger.info(f"Agent created ethics ContentItem: {item.title} (id={item.id})")
    return f"Created ethics policy content '{item.title}' (id={item.id}) in pending_review status. It will appear in Governance > Content for review."


# Map tool names to @function_tool objects for mission-based selection
ALL_TOOLS = {
    "search_existing_records": search_existing_records,
    "create_media_organization": create_media_organization,
    "create_discovered_tool": create_discovered_tool,
    "create_use_case": create_use_case,
    "create_legal_framework_content": create_legal_framework_content,
    "create_ethics_policy_content": create_ethics_policy_content,
}
