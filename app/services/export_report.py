"""Export/Report Generation service.

Gathers user's AI implementation artifacts (ethics policy, legal framework,
strategy plan, tool reviews, readiness assessment) and renders them into
a downloadable HTML report.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.ethics_builder import EthicsPolicy, EthicsPolicyVersion
from app.models.legal_builder import LegalFrameworkDoc, LegalFrameworkVersion
from app.models.toolkit import StrategyPlan
from app.models.review import ToolReview
from app.models.readiness import ReadinessAssessment
from app.models.progress import UserProgress
from app.services.progress_tracker import refresh_progress

logger = logging.getLogger(__name__)


def get_report_sections(db: Session, user_id) -> dict[str, Any]:
    """Fetch all available content sections for a user's report.

    Returns a dict with keys for each section and their content,
    or None if the section doesn't exist yet.
    """
    sections: dict[str, Any] = {}

    # Ethics Policy (latest published version)
    ethics_version = (
        db.query(EthicsPolicyVersion)
        .join(EthicsPolicy, EthicsPolicyVersion.policy_id == EthicsPolicy.id)
        .filter(
            EthicsPolicy.user_id == user_id,
            EthicsPolicyVersion.status == "published",
        )
        .order_by(EthicsPolicyVersion.version_number.desc())
        .first()
    )
    if ethics_version:
        policy = db.query(EthicsPolicy).filter(EthicsPolicy.id == ethics_version.policy_id).first()
        sections["ethics_policy"] = {
            "title": policy.title if policy else "AI Ethics Policy",
            "content_markdown": ethics_version.content_markdown,
            "sections_data": ethics_version.sections_data,
            "version": ethics_version.version_number,
            "published_at": ethics_version.published_at,
        }

    # Legal Framework (latest published version)
    legal_version = (
        db.query(LegalFrameworkVersion)
        .join(LegalFrameworkDoc, LegalFrameworkVersion.framework_id == LegalFrameworkDoc.id)
        .filter(
            LegalFrameworkDoc.user_id == user_id,
            LegalFrameworkVersion.status == "published",
        )
        .order_by(LegalFrameworkVersion.version_number.desc())
        .first()
    )
    if legal_version:
        framework = db.query(LegalFrameworkDoc).filter(LegalFrameworkDoc.id == legal_version.framework_id).first()
        sections["legal_framework"] = {
            "title": framework.title if framework else "AI Legal Framework",
            "narrative_markdown": legal_version.narrative_markdown,
            "checklist_items": legal_version.checklist_items or [],
            "framework_config": legal_version.framework_config or {},
            "version": legal_version.version_number,
            "published_at": legal_version.published_at,
        }

    # Strategy Plan (most recent)
    strategy = (
        db.query(StrategyPlan)
        .filter(StrategyPlan.user_id == user_id)
        .order_by(StrategyPlan.created_at.desc())
        .first()
    )
    if strategy:
        sections["strategy_plan"] = {
            "plan_text": strategy.plan_text,
            "inputs": strategy.inputs or {},
            "created_at": strategy.created_at,
        }

    # Tool Reviews
    reviews = (
        db.query(ToolReview)
        .filter(
            ToolReview.user_id == user_id,
            ToolReview.is_hidden == False,
        )
        .order_by(ToolReview.created_at.desc())
        .all()
    )
    if reviews:
        sections["tool_reviews"] = [
            {
                "tool_slug": r.tool_slug,
                "rating": r.rating,
                "comment": r.comment,
                "use_case_tag": r.use_case_tag,
                "created_at": r.created_at,
            }
            for r in reviews
        ]

    # Readiness Assessment (most recent)
    assessment = (
        db.query(ReadinessAssessment)
        .filter(ReadinessAssessment.user_id == user_id)
        .order_by(ReadinessAssessment.created_at.desc())
        .first()
    )
    if assessment:
        sections["readiness"] = {
            "overall_score": assessment.overall_score,
            "maturity_level": assessment.maturity_level,
            "dimension_scores": assessment.dimension_scores or {},
            "recommendations": assessment.recommendations or [],
            "created_at": assessment.created_at,
        }

    # Progress summary
    progress = refresh_progress(db, user_id)
    sections["progress"] = {
        "overall_pct": progress.overall_completion_pct,
        "ethics_complete": progress.ethics_policy_complete,
        "legal_complete": progress.legal_framework_complete,
        "strategy_complete": progress.strategy_plan_complete,
        "readiness_complete": progress.readiness_assessment_complete,
        "tools_evaluated": progress.tools_evaluated_count,
    }

    return sections


def get_available_sections_summary(db: Session, user_id) -> list[dict]:
    """Get a summary of which sections are available for the report.

    Returns a list of dicts with label, available (bool), and route to complete.
    """
    sections = get_report_sections(db, user_id)

    return [
        {
            "label": "AI Ethics Policy",
            "key": "ethics_policy",
            "available": "ethics_policy" in sections,
            "route": "/ethics-builder",
        },
        {
            "label": "Legal Framework",
            "key": "legal_framework",
            "available": "legal_framework" in sections,
            "route": "/legal-builder",
        },
        {
            "label": "Strategy Plan",
            "key": "strategy_plan",
            "available": "strategy_plan" in sections,
            "route": "/strategy",
        },
        {
            "label": "Tool Reviews",
            "key": "tool_reviews",
            "available": "tool_reviews" in sections,
            "route": "/tools",
        },
        {
            "label": "AI Readiness Assessment",
            "key": "readiness",
            "available": "readiness" in sections,
            "route": "/readiness",
        },
        {
            "label": "Progress Summary",
            "key": "progress",
            "available": True,
            "route": "/progress",
        },
    ]
