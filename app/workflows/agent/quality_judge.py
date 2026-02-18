"""Post-run quality assessment for agent-created records.

After each agent mission completes, this module reviews the created records,
scores them on completeness criteria, and auto-rejects low-quality entries.
"""
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.directory import MediaOrganization
from app.models.discovery import DiscoveredTool
from app.models.usecase import UseCase
from app.models.governance import ContentItem

logger = logging.getLogger(__name__)

# Map tool names to their record type label
TOOL_TO_TYPE = {
    "create_media_organization": "organization",
    "create_discovered_tool": "tool",
    "create_use_case": "use_case",
    "create_legal_framework_content": "content",
    "create_ethics_policy_content": "content",
}


def _judge_organization(db: Session, name: str) -> dict[str, Any]:
    """Score a MediaOrganization record."""
    org = (
        db.query(MediaOrganization)
        .filter(MediaOrganization.name.ilike(name))
        .first()
    )
    if not org:
        return {"score": 0, "quality": "low", "issues": ["record not found"], "checks_passed": 0, "checks_total": 5}

    issues = []
    checks = 5
    passed = 0

    if org.name and org.name.strip():
        passed += 1
    else:
        issues.append("missing name")

    if org.website and org.website.strip():
        passed += 1
    else:
        issues.append("missing website URL")

    if org.country and org.country.strip():
        passed += 1
    else:
        issues.append("missing country")

    if org.description and len(org.description.strip()) > 20:
        passed += 1
    else:
        issues.append("description too short or missing")

    if org.website and "." in org.website:
        passed += 1
    else:
        issues.append("website URL looks invalid")

    score = passed / checks
    quality = "high" if score >= 0.8 else ("medium" if score >= 0.5 else "low")

    return {
        "score": round(score, 2),
        "quality": quality,
        "issues": issues,
        "checks_passed": passed,
        "checks_total": checks,
        "record_id": str(org.id) if org else None,
    }


def _judge_tool(db: Session, name: str) -> dict[str, Any]:
    """Score a DiscoveredTool record."""
    tool = (
        db.query(DiscoveredTool)
        .filter(DiscoveredTool.name.ilike(name))
        .first()
    )
    if not tool:
        return {"score": 0, "quality": "low", "issues": ["record not found"], "checks_passed": 0, "checks_total": 5}

    issues = []
    checks = 5
    passed = 0

    if tool.name and tool.name.strip():
        passed += 1
    else:
        issues.append("missing name")

    if tool.url and tool.url.strip():
        passed += 1
    else:
        issues.append("missing URL")

    if tool.url and tool.url_domain and "." in tool.url_domain:
        passed += 1
    else:
        issues.append("URL domain looks invalid")

    if tool.description and len(tool.description.strip()) > 30:
        passed += 1
    else:
        issues.append("description too short or missing")

    if tool.categories and len(tool.categories) > 0:
        passed += 1
    else:
        issues.append("no category")

    score = passed / checks
    quality = "high" if score >= 0.8 else ("medium" if score >= 0.5 else "low")

    return {
        "score": round(score, 2),
        "quality": quality,
        "issues": issues,
        "checks_passed": passed,
        "checks_total": checks,
        "record_id": str(tool.id) if tool else None,
    }


def _judge_use_case(db: Session, name: str) -> dict[str, Any]:
    """Score a UseCase record."""
    uc = (
        db.query(UseCase)
        .filter(UseCase.title.ilike(name))
        .first()
    )
    if not uc:
        return {"score": 0, "quality": "low", "issues": ["record not found"], "checks_passed": 0, "checks_total": 5}

    issues = []
    checks = 5
    passed = 0

    if uc.title and uc.title.strip():
        passed += 1
    else:
        issues.append("missing title")

    if uc.organization and uc.organization.strip():
        passed += 1
    else:
        issues.append("missing organization")

    if uc.summary and len(uc.summary.strip()) > 50:
        passed += 1
    else:
        issues.append("summary too short or missing")

    if uc.source_url and uc.source_url.strip():
        passed += 1
    else:
        issues.append("missing source URL")

    has_cso = bool(
        (uc.challenge and uc.challenge.strip())
        and (uc.solution and uc.solution.strip())
        and (uc.outcome and uc.outcome.strip())
    )
    if has_cso:
        passed += 1
    else:
        issues.append("missing challenge/solution/outcome")

    score = passed / checks
    quality = "high" if score >= 0.8 else ("medium" if score >= 0.5 else "low")

    return {
        "score": round(score, 2),
        "quality": quality,
        "issues": issues,
        "checks_passed": passed,
        "checks_total": checks,
        "record_id": str(uc.id) if uc else None,
    }


def _judge_content(db: Session, name: str) -> dict[str, Any]:
    """Score a ContentItem record (legal framework or ethics policy)."""
    item = (
        db.query(ContentItem)
        .filter(ContentItem.title.ilike(name))
        .first()
    )
    if not item:
        return {"score": 0, "quality": "low", "issues": ["record not found"], "checks_passed": 0, "checks_total": 4}

    issues = []
    checks = 4
    passed = 0

    if item.title and item.title.strip():
        passed += 1
    else:
        issues.append("missing title")

    if item.content_markdown and len(item.content_markdown.strip()) > 100:
        passed += 1
    else:
        issues.append("content too short or missing")

    if item.summary and item.summary.strip():
        passed += 1
    else:
        issues.append("missing summary")

    has_source = item.sources and len(item.sources) > 0 and any(
        s.get("url") for s in item.sources if isinstance(s, dict)
    )
    if has_source:
        passed += 1
    else:
        issues.append("missing source URL")

    score = passed / checks
    quality = "high" if score >= 0.8 else ("medium" if score >= 0.5 else "low")

    return {
        "score": round(score, 2),
        "quality": quality,
        "issues": issues,
        "checks_passed": passed,
        "checks_total": checks,
        "record_id": str(item.id) if item else None,
    }


# Map tool to judge function
_JUDGE_FNS = {
    "create_media_organization": _judge_organization,
    "create_discovered_tool": _judge_tool,
    "create_use_case": _judge_use_case,
    "create_legal_framework_content": _judge_content,
    "create_ethics_policy_content": _judge_content,
}


async def judge_mission_results(
    db: Session,
    run_id: str,
    created_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Assess quality of all records created by a mission run.

    Auto-rejects records scoring below 0.5 and returns a quality report.
    """
    details: list[dict[str, Any]] = []
    high = medium = low = rejected = 0

    for record in created_records:
        tool_name = record.get("tool", "")
        record_name = record.get("name", "")
        record_type = TOOL_TO_TYPE.get(tool_name, "unknown")

        judge_fn = _JUDGE_FNS.get(tool_name)
        if not judge_fn:
            details.append({
                "name": record_name,
                "type": record_type,
                "score": 0,
                "quality": "unknown",
                "issues": [f"no judge for tool: {tool_name}"],
            })
            continue

        result = judge_fn(db, record_name)

        entry: dict[str, Any] = {
            "name": record_name,
            "type": record_type,
            "score": result["score"],
            "quality": result["quality"],
            "issues": result["issues"],
        }

        if result["quality"] == "high":
            high += 1
        elif result["quality"] == "medium":
            medium += 1
        else:
            low += 1
            # Auto-reject low quality records
            _auto_reject(db, tool_name, record_name)
            entry["action"] = "auto_rejected"
            rejected += 1

        details.append(entry)

    db.commit()

    report = {
        "total_records": len(created_records),
        "high_quality": high,
        "medium_quality": medium,
        "low_quality": low,
        "auto_rejected": rejected,
        "details": details,
    }

    logger.info(
        f"Quality report for run {run_id}: "
        f"{high} high, {medium} medium, {low} low, {rejected} auto-rejected"
    )

    return report


def _auto_reject(db: Session, tool_name: str, name: str) -> None:
    """Flag a low-quality record as rejected."""
    try:
        if tool_name == "create_media_organization":
            record = db.query(MediaOrganization).filter(MediaOrganization.name.ilike(name)).first()
            if record:
                record.notes = (record.notes or "") + "\n[auto-rejected: low quality score]"
                record.is_active = False

        elif tool_name == "create_discovered_tool":
            record = db.query(DiscoveredTool).filter(DiscoveredTool.name.ilike(name)).first()
            if record:
                record.status = "rejected"
                record.review_notes = "auto-rejected: low quality score"

        elif tool_name == "create_use_case":
            record = db.query(UseCase).filter(UseCase.title.ilike(name)).first()
            if record:
                record.status = "rejected"
                record.review_notes = "auto-rejected: low quality score"

        elif tool_name in ("create_legal_framework_content", "create_ethics_policy_content"):
            record = db.query(ContentItem).filter(ContentItem.title.ilike(name)).first()
            if record:
                record.status = "rejected"
                record.review_notes = "auto-rejected: low quality score"

    except Exception as e:
        logger.error(f"Error auto-rejecting {name}: {e}")
