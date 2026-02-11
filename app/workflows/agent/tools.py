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
        record_type: Type of record to search for. Must be 'organization' or 'tool'.
        query: Search query matched against name via case-insensitive contains.
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

    else:
        return f"Error: unknown record_type '{record_type}'. Use 'organization' or 'tool'."

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


# Map tool names to @function_tool objects for mission-based selection
ALL_TOOLS = {
    "search_existing_records": search_existing_records,
    "create_media_organization": create_media_organization,
    "create_discovered_tool": create_discovered_tool,
}
