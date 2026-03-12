"""User progress tracking service.

Calculates and caches a user's AI implementation progress
by querying actual completion state from the database.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.progress import UserProgress
from app.models.ethics_builder import EthicsPolicy, EthicsPolicyVersion
from app.models.legal_builder import LegalFrameworkDoc, LegalFrameworkVersion
from app.models.toolkit import StrategyPlan
from app.models.review import ToolReview

logger = logging.getLogger(__name__)


def get_or_create_progress(db: Session, user_id) -> UserProgress:
    """Get or lazily create a progress record for a user."""
    progress = (
        db.query(UserProgress)
        .filter(UserProgress.user_id == user_id)
        .first()
    )
    if not progress:
        progress = UserProgress(user_id=user_id)
        db.add(progress)
        db.commit()
        db.refresh(progress)
    return progress


def refresh_progress(db: Session, user_id) -> UserProgress:
    """Recalculate progress from actual database state.

    Checks:
    - Ethics policy: has a published EthicsPolicyVersion
    - Legal framework: has a published LegalFrameworkVersion
    - Strategy plan: has at least one StrategyPlan
    - Tools evaluated: count of ToolReview records
    - Readiness assessment: checked later when that feature exists
    """
    progress = get_or_create_progress(db, user_id)

    # Ethics policy — check for a published version
    has_ethics = (
        db.query(EthicsPolicyVersion)
        .join(EthicsPolicy, EthicsPolicyVersion.policy_id == EthicsPolicy.id)
        .filter(
            EthicsPolicy.user_id == user_id,
            EthicsPolicyVersion.status == "published",
        )
        .first()
    ) is not None
    progress.ethics_policy_complete = has_ethics

    # Legal framework — check for a published version
    has_legal = (
        db.query(LegalFrameworkVersion)
        .join(LegalFrameworkDoc, LegalFrameworkVersion.framework_id == LegalFrameworkDoc.id)
        .filter(
            LegalFrameworkDoc.user_id == user_id,
            LegalFrameworkVersion.status == "published",
        )
        .first()
    ) is not None
    progress.legal_framework_complete = has_legal

    # Strategy plan — check for any plan
    has_strategy = (
        db.query(StrategyPlan)
        .filter(StrategyPlan.user_id == user_id)
        .first()
    ) is not None
    progress.strategy_plan_complete = has_strategy

    # Tools evaluated — count of reviews by user
    tools_count = (
        db.query(func.count(ToolReview.id))
        .filter(ToolReview.user_id == user_id)
        .scalar()
    ) or 0
    progress.tools_evaluated_count = tools_count

    # Readiness assessment — check if table exists and user has one
    try:
        from app.models.readiness import ReadinessAssessment
        has_readiness = (
            db.query(ReadinessAssessment)
            .filter(ReadinessAssessment.user_id == user_id)
            .first()
        ) is not None
        progress.readiness_assessment_complete = has_readiness
    except Exception:
        pass  # Table may not exist yet

    # Calculate overall completion percentage
    progress.overall_completion_pct = _calculate_completion(progress)
    progress.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(progress)
    return progress


def _calculate_completion(progress: UserProgress) -> float:
    """Calculate overall completion percentage.

    Weights:
    - Ethics policy: 25%
    - Legal framework: 25%
    - Strategy plan: 20%
    - Readiness assessment: 15%
    - Tools evaluated (at least 3): 15%
    """
    score = 0.0
    if progress.ethics_policy_complete:
        score += 25.0
    if progress.legal_framework_complete:
        score += 25.0
    if progress.strategy_plan_complete:
        score += 20.0
    if progress.readiness_assessment_complete:
        score += 15.0
    if progress.tools_evaluated_count >= 3:
        score += 15.0
    elif progress.tools_evaluated_count > 0:
        score += 15.0 * (progress.tools_evaluated_count / 3.0)
    return round(score, 1)


def get_progress_summary(db: Session, user_id) -> dict:
    """Get a lightweight summary dict for the sidebar widget."""
    progress = refresh_progress(db, user_id)
    return {
        "overall_pct": progress.overall_completion_pct,
        "items": [
            {
                "label": "Ethics Policy",
                "complete": progress.ethics_policy_complete,
                "route": "/ethics-builder",
            },
            {
                "label": "Legal Framework",
                "complete": progress.legal_framework_complete,
                "route": "/legal-builder",
            },
            {
                "label": "Strategy Plan",
                "complete": progress.strategy_plan_complete,
                "route": "/strategy",
            },
            {
                "label": "AI Readiness",
                "complete": progress.readiness_assessment_complete,
                "route": "/readiness",
            },
            {
                "label": f"Tools Evaluated ({progress.tools_evaluated_count})",
                "complete": progress.tools_evaluated_count >= 3,
                "route": "/tools",
            },
        ],
    }
