"""Client-side tool definitions for the AI agent.

Each tool is defined as:
- An async handler function that performs the DB operation
- A schema dict describing the tool for Claude's tool-use API
"""
import re
import logging
from sqlalchemy.orm import Session
from app.models.directory import MediaOrganization
from app.models.discovery import DiscoveredTool

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool schemas (sent to Claude API)
# ---------------------------------------------------------------------------

SEARCH_EXISTING_RECORDS_SCHEMA = {
    "name": "search_existing_records",
    "description": (
        "Search for existing records in the database to check for duplicates "
        "before creating new ones. Returns matching names and IDs."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "record_type": {
                "type": "string",
                "enum": ["organization", "tool"],
                "description": "Type of record to search for.",
            },
            "query": {
                "type": "string",
                "description": "Search query (matched against name/title via case-insensitive contains).",
            },
        },
        "required": ["record_type", "query"],
    },
}

CREATE_MEDIA_ORGANIZATION_SCHEMA = {
    "name": "create_media_organization",
    "description": (
        "Create a new media organization record in draft status. "
        "Always search_existing_records first to avoid duplicates."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Organization name."},
            "org_type": {
                "type": "string",
                "enum": ["newspaper", "broadcaster", "digital", "agency", "freelance_collective"],
                "description": "Type of media organization.",
            },
            "website": {"type": "string", "description": "Organization website URL."},
            "country": {"type": "string", "description": "Country of operation."},
            "description": {"type": "string", "description": "Brief description of the organization."},
            "notes": {"type": "string", "description": "Additional context (ownership, coverage areas, etc.)."},
        },
        "required": ["name", "org_type"],
    },
}

CREATE_DISCOVERED_TOOL_SCHEMA = {
    "name": "create_discovered_tool",
    "description": (
        "Create a new discovered tool record in pending_review status. "
        "Always search_existing_records first to avoid duplicates."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Tool name."},
            "url": {"type": "string", "description": "Tool website URL."},
            "description": {"type": "string", "description": "What the tool does."},
            "category": {"type": "string", "description": "Primary category (e.g. fact-checking, transcription)."},
            "pricing_model": {
                "type": "string",
                "enum": ["free", "freemium", "paid", "open_source", "enterprise"],
                "description": "Pricing model.",
            },
            "features": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of key features.",
            },
        },
        "required": ["name", "url", "description"],
    },
}

ALL_TOOL_SCHEMAS = {
    "search_existing_records": SEARCH_EXISTING_RECORDS_SCHEMA,
    "create_media_organization": CREATE_MEDIA_ORGANIZATION_SCHEMA,
    "create_discovered_tool": CREATE_DISCOVERED_TOOL_SCHEMA,
}


# ---------------------------------------------------------------------------
# Tool handlers
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


async def handle_search_existing_records(db: Session, params: dict) -> str:
    """Search existing records by name/title."""
    record_type = params.get("record_type", "organization")
    query = params.get("query", "").strip()

    if not query:
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


async def handle_create_media_organization(db: Session, params: dict, run_id: str) -> str:
    """Create a MediaOrganization in draft status."""
    name = params.get("name", "").strip()
    if not name:
        return "Error: name is required."

    # Check for exact duplicate
    existing = (
        db.query(MediaOrganization)
        .filter(MediaOrganization.name.ilike(name))
        .first()
    )
    if existing:
        return f"Duplicate: organization '{existing.name}' already exists (id={existing.id}). Skipped."

    org = MediaOrganization(
        name=name,
        org_type=params.get("org_type", "digital"),
        website=params.get("website"),
        country=params.get("country"),
        description=params.get("description"),
        notes=params.get("notes", "") + f"\n[source=agent, run_id={run_id}]",
        is_active=False,  # Draft — not active until admin approves
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    logger.info(f"Agent created MediaOrganization: {org.name} (id={org.id})")
    return f"Created organization '{org.name}' (id={org.id}) in draft status."


async def handle_create_discovered_tool(db: Session, params: dict, run_id: str) -> str:
    """Create a DiscoveredTool in pending_review status."""
    name = params.get("name", "").strip()
    url = params.get("url", "").strip()
    if not name or not url:
        return "Error: name and url are required."

    slug = _slugify(name)
    domain = _extract_domain(url)

    # Check for duplicate by slug or domain+name
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
        description=params.get("description"),
        categories=([params["category"]] if params.get("category") else []),
        tags=params.get("features", []),
        source_type="directory",
        source_url="agent",
        source_name=f"AI Agent (run {run_id})",
        status="pending_review",
        confidence_score=0.7,
        extra_data={
            "pricing_model": params.get("pricing_model"),
            "agent_run_id": run_id,
        },
    )
    db.add(tool)
    db.commit()
    db.refresh(tool)

    logger.info(f"Agent created DiscoveredTool: {tool.name} (id={tool.id})")
    return f"Created tool '{tool.name}' (id={tool.id}) in pending_review status."


# Map tool names to handlers
TOOL_HANDLERS = {
    "search_existing_records": handle_search_existing_records,
    "create_media_organization": handle_create_media_organization,
    "create_discovered_tool": handle_create_discovered_tool,
}
