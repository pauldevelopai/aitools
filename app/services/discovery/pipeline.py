"""Main discovery pipeline service."""
import asyncio
import logging
import re
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import DiscoveredTool, DiscoveryRun, ToolMatch
from app.services.discovery.sources import DiscoverySource, RawToolData
from app.services.discovery.dedup import (
    deduplicate_tool,
    create_match_records,
    extract_domain,
    normalize_name
)

logger = logging.getLogger(__name__)


def generate_slug(name: str, existing_slugs: set[str] | None = None) -> str:
    """
    Generate a URL-friendly slug from tool name.

    Args:
        name: Tool name
        existing_slugs: Set of existing slugs to avoid collisions

    Returns:
        Unique slug
    """
    # Convert to lowercase and replace spaces/special chars with hyphens
    slug = re.sub(r'[^\w\s-]', '', name.lower())
    slug = re.sub(r'[-\s]+', '-', slug).strip('-')

    # Ensure uniqueness if existing_slugs provided
    if existing_slugs:
        base_slug = slug
        counter = 1
        while slug in existing_slugs:
            slug = f"{base_slug}-{counter}"
            counter += 1

    return slug


def get_all_sources() -> list[DiscoverySource]:
    """Get all available discovery sources."""
    from app.services.discovery.github_source import (
        GitHubTrendingSource,
        GitHubAwesomeListSource
    )
    from app.services.discovery.producthunt_source import ProductHuntSource
    from app.services.discovery.directory_source import DirectorySource

    return [
        GitHubTrendingSource(),
        GitHubAwesomeListSource(),
        ProductHuntSource(),
        DirectorySource(),
    ]


def get_sources_by_type(source_types: list[str]) -> list[DiscoverySource]:
    """Get discovery sources filtered by type."""
    all_sources = get_all_sources()
    return [s for s in all_sources if s.source_type in source_types]


async def run_discovery_pipeline(
    db: Session,
    sources: list[str] | None = None,
    dry_run: bool = False,
    triggered_by: str = "manual",
    config: dict | None = None
) -> DiscoveryRun:
    """
    Run the discovery pipeline across specified sources.

    Args:
        db: Database session
        sources: List of source types to run (None = all sources)
            Options: "github", "producthunt", "awesome_list", "directory"
        dry_run: If True, don't save to database
        triggered_by: Who triggered this run ("manual", "cron", or user ID)
        config: Optional configuration overrides for sources

    Returns:
        DiscoveryRun record with stats
    """
    # Create run record
    run = DiscoveryRun(
        status="running",
        source_type=",".join(sources) if sources else None,
        triggered_by=triggered_by,
        run_config=config or {}
    )

    if not dry_run:
        db.add(run)
        db.commit()
        db.refresh(run)

    try:
        # Get sources to run
        if sources:
            discovery_sources = get_sources_by_type(sources)
        else:
            discovery_sources = get_all_sources()

        if not discovery_sources:
            raise ValueError(f"No valid sources found for: {sources}")

        # Load existing tools and slugs for deduplication
        existing_tools = db.query(DiscoveredTool).filter(
            DiscoveredTool.status != "rejected"
        ).all()
        existing_slugs = {t.slug for t in existing_tools}

        # Load kit tools for cross-reference
        kit_tools = _load_kit_tools()

        # Stats tracking
        tools_found = 0
        tools_new = 0
        tools_updated = 0
        tools_skipped = 0

        # Run each source
        for source in discovery_sources:
            logger.info(f"Running discovery source: {source.name}")

            try:
                # Fetch tools from source
                source_config = (config or {}).get(source.source_type, {})
                raw_tools = await source.discover(source_config)
                tools_found += len(raw_tools)

                # Process each tool
                for raw_tool in raw_tools:
                    result = process_discovered_tool(
                        db=db,
                        raw_tool=raw_tool,
                        source=source,
                        existing_tools=existing_tools,
                        existing_slugs=existing_slugs,
                        kit_tools=kit_tools,
                        dry_run=dry_run
                    )

                    if result == "new":
                        tools_new += 1
                    elif result == "updated":
                        tools_updated += 1
                    elif result == "skipped":
                        tools_skipped += 1

            except Exception as e:
                logger.error(f"Error running source {source.name}: {e}")
                continue

        # Update run record
        run.status = "completed"
        run.completed_at = datetime.utcnow()
        run.tools_found = tools_found
        run.tools_new = tools_new
        run.tools_updated = tools_updated
        run.tools_skipped = tools_skipped

        if not dry_run:
            db.commit()

        logger.info(
            f"Discovery completed: {tools_found} found, {tools_new} new, "
            f"{tools_updated} updated, {tools_skipped} skipped"
        )

    except Exception as e:
        logger.error(f"Discovery pipeline failed: {e}")
        run.status = "failed"
        run.error_message = str(e)
        run.completed_at = datetime.utcnow()

        if not dry_run:
            db.commit()

        raise

    return run


def process_discovered_tool(
    db: Session,
    raw_tool: RawToolData,
    source: DiscoverySource,
    existing_tools: list[DiscoveredTool],
    existing_slugs: set[str],
    kit_tools: list[dict] | None = None,
    dry_run: bool = False
) -> str:
    """
    Process a single discovered tool.

    Args:
        db: Database session
        raw_tool: Raw tool data from source
        source: The discovery source
        existing_tools: Existing discovered tools
        existing_slugs: Existing slugs for collision detection
        kit_tools: Curated kit tools for dedup
        dry_run: If True, don't save to database

    Returns:
        "new", "updated", or "skipped"
    """
    try:
        # Extract domain for deduplication
        url_domain = extract_domain(raw_tool.url)

        # Check if we already have this exact URL
        existing_by_url = next(
            (t for t in existing_tools
             if t.url.lower().strip().rstrip("/") == raw_tool.url.lower().strip().rstrip("/")),
            None
        )

        if existing_by_url:
            # Update last_seen_at
            if not dry_run:
                existing_by_url.last_seen_at = datetime.utcnow()
                if raw_tool.description and not existing_by_url.description:
                    existing_by_url.description = raw_tool.description
                db.commit()
            return "updated"

        # Run deduplication
        is_duplicate, matches, confidence_score = deduplicate_tool(
            db=db,
            raw_tool=raw_tool,
            existing_tools=existing_tools,
            kit_tools=kit_tools
        )

        # Skip definite duplicates (exact URL or domain match)
        if is_duplicate and any(m.match_score >= 0.9 for m in matches):
            logger.debug(f"Skipping duplicate: {raw_tool.name} ({raw_tool.url})")
            return "skipped"

        # Generate unique slug
        slug = generate_slug(raw_tool.name, existing_slugs)
        existing_slugs.add(slug)

        # Determine initial status based on confidence
        if confidence_score < 0.5:
            status = "pending_review"
        elif confidence_score < 0.7:
            status = "pending_review"
        else:
            # High confidence new tool, still needs review but can be auto-approved
            status = "pending_review"

        # Create tool record
        tool = DiscoveredTool(
            name=raw_tool.name,
            slug=slug,
            url=raw_tool.url,
            url_domain=url_domain,
            docs_url=raw_tool.docs_url,
            pricing_url=raw_tool.pricing_url,
            description=raw_tool.description,
            raw_description=raw_tool.description,
            categories=raw_tool.categories or [],
            tags=raw_tool.tags or [],
            source_type=source.source_type,
            source_url=raw_tool.source_url,
            source_name=source.name,
            last_updated_signal=raw_tool.last_updated,
            extra_data=raw_tool.extra_data or {},
            status=status,
            confidence_score=confidence_score
        )

        if not dry_run:
            db.add(tool)
            db.flush()  # Get the ID

            # Create match records for potential duplicates
            if matches:
                create_match_records(db, tool, matches)

            db.commit()

            # Add to existing tools for subsequent dedup checks
            existing_tools.append(tool)

        logger.info(f"Discovered new tool: {raw_tool.name} (confidence: {confidence_score:.2f})")
        return "new"

    except Exception as e:
        logger.error(f"Error processing tool {raw_tool.name}: {e}")
        db.rollback()
        return "skipped"


def _load_kit_tools() -> list[dict]:
    """Load curated kit tools for deduplication."""
    try:
        from app.services.kit_loader import load_all_tools
        tools = load_all_tools()
        return tools
    except Exception as e:
        logger.warning(f"Could not load kit tools: {e}")
        return []


async def run_single_source(
    db: Session,
    source_type: str,
    triggered_by: str = "manual",
    config: dict | None = None
) -> DiscoveryRun:
    """
    Run discovery for a single source type.

    Convenience wrapper around run_discovery_pipeline.
    """
    return await run_discovery_pipeline(
        db=db,
        sources=[source_type],
        triggered_by=triggered_by,
        config=config
    )


def get_pending_tools(db: Session, limit: int = 100, offset: int = 0) -> list[DiscoveredTool]:
    """Get tools pending review."""
    return db.query(DiscoveredTool).filter(
        DiscoveredTool.status == "pending_review"
    ).order_by(
        DiscoveredTool.confidence_score.asc(),  # Lowest confidence first (needs most review)
        DiscoveredTool.discovered_at.desc()
    ).offset(offset).limit(limit).all()


def get_tool_matches(db: Session, tool_id: str) -> list[ToolMatch]:
    """Get all potential matches for a discovered tool."""
    return db.query(ToolMatch).filter(
        ToolMatch.tool_id == tool_id,
        ToolMatch.is_duplicate.is_(None)  # Unresolved matches
    ).order_by(ToolMatch.match_score.desc()).all()


def approve_tool(
    db: Session,
    tool_id: str,
    user_id: str,
    notes: str | None = None
) -> DiscoveredTool:
    """Approve a discovered tool."""
    tool = db.query(DiscoveredTool).filter(DiscoveredTool.id == tool_id).first()
    if not tool:
        raise ValueError(f"Tool not found: {tool_id}")

    tool.status = "approved"
    tool.reviewed_by = user_id
    tool.reviewed_at = datetime.utcnow()
    tool.review_notes = notes

    db.commit()
    db.refresh(tool)
    return tool


def reject_tool(
    db: Session,
    tool_id: str,
    user_id: str,
    notes: str | None = None
) -> DiscoveredTool:
    """Reject a discovered tool."""
    tool = db.query(DiscoveredTool).filter(DiscoveredTool.id == tool_id).first()
    if not tool:
        raise ValueError(f"Tool not found: {tool_id}")

    tool.status = "rejected"
    tool.reviewed_by = user_id
    tool.reviewed_at = datetime.utcnow()
    tool.review_notes = notes

    db.commit()
    db.refresh(tool)
    return tool


def resolve_match(
    db: Session,
    match_id: str,
    is_duplicate: bool,
    user_id: str,
    notes: str | None = None
) -> ToolMatch:
    """Resolve a potential duplicate match."""
    match = db.query(ToolMatch).filter(ToolMatch.id == match_id).first()
    if not match:
        raise ValueError(f"Match not found: {match_id}")

    match.is_duplicate = is_duplicate
    match.resolved_by = user_id
    match.resolved_at = datetime.utcnow()
    match.resolution_notes = notes

    db.commit()
    db.refresh(match)
    return match
