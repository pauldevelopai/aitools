"""Admin insights service — aggregated analytics across all users and orgs."""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.ethics_builder import EthicsPolicy, EthicsPolicyVersion
from app.models.legal_builder import LegalFrameworkDoc, LegalFrameworkVersion
from app.models.toolkit import StrategyPlan, ChatLog
from app.models.review import ToolReview
from app.models.readiness import ReadinessAssessment
from app.models.brain import KnowledgeGap

logger = logging.getLogger(__name__)


def get_onboarding_funnel(db: Session) -> dict:
    """Count users at each stage of the implementation funnel."""
    total_users = db.query(func.count(User.id)).filter(User.is_admin == False).scalar() or 0

    # Profile complete: has org type and role
    profile_complete = (
        db.query(func.count(User.id))
        .filter(User.is_admin == False, User.organisation_type.isnot(None), User.role.isnot(None))
        .scalar() or 0
    )

    # Has done readiness assessment
    assessment_done = (
        db.query(func.count(func.distinct(ReadinessAssessment.user_id)))
        .filter(ReadinessAssessment.user_id.isnot(None))
        .scalar() or 0
    )

    # Has published ethics policy
    ethics_done = (
        db.query(func.count(func.distinct(EthicsPolicy.user_id)))
        .join(EthicsPolicyVersion, EthicsPolicyVersion.policy_id == EthicsPolicy.id)
        .filter(EthicsPolicyVersion.status == "published")
        .scalar() or 0
    )

    # Has published legal framework
    legal_done = (
        db.query(func.count(func.distinct(LegalFrameworkDoc.user_id)))
        .join(LegalFrameworkVersion, LegalFrameworkVersion.framework_id == LegalFrameworkDoc.id)
        .filter(LegalFrameworkVersion.status == "published")
        .scalar() or 0
    )

    # Has strategy plan
    strategy_done = (
        db.query(func.count(func.distinct(StrategyPlan.user_id))).scalar() or 0
    )

    return {
        "total_users": total_users,
        "profile_complete": profile_complete,
        "assessment_done": assessment_done,
        "ethics_done": ethics_done,
        "legal_done": legal_done,
        "strategy_done": strategy_done,
    }


def get_orgs_without_policies(db: Session, limit: int = 20) -> list[dict]:
    """Users registered >7 days ago with no ethics or legal policy."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    # Get users who have ethics policies
    users_with_ethics = (
        db.query(EthicsPolicy.user_id)
        .join(EthicsPolicyVersion, EthicsPolicyVersion.policy_id == EthicsPolicy.id)
        .filter(EthicsPolicyVersion.status == "published")
        .subquery()
    )

    users = (
        db.query(User)
        .filter(
            User.is_admin == False,
            User.created_at < cutoff,
            ~User.id.in_(db.query(users_with_ethics.c.user_id)),
        )
        .order_by(User.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": str(u.id),
            "email": u.email,
            "username": u.username,
            "organisation": u.organisation,
            "organisation_type": u.organisation_type,
            "registered": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


def get_sector_breakdown(db: Session) -> dict:
    """User count by organisation type."""
    rows = (
        db.query(User.organisation_type, func.count(User.id))
        .filter(User.is_admin == False, User.organisation_type.isnot(None))
        .group_by(User.organisation_type)
        .all()
    )
    return {org_type or "unknown": count for org_type, count in rows}


def get_geographic_distribution(db: Session) -> list[dict]:
    """User count by country."""
    rows = (
        db.query(User.country, func.count(User.id))
        .filter(User.is_admin == False, User.country.isnot(None))
        .group_by(User.country)
        .order_by(func.count(User.id).desc())
        .limit(20)
        .all()
    )
    return [{"country": country, "count": count} for country, count in rows]


def get_engagement_metrics(db: Session) -> dict:
    """Active users and usage stats."""
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    active_7d = (
        db.query(func.count(func.distinct(ChatLog.user_id)))
        .filter(ChatLog.created_at >= week_ago)
        .scalar() or 0
    )

    active_30d = (
        db.query(func.count(func.distinct(ChatLog.user_id)))
        .filter(ChatLog.created_at >= month_ago)
        .scalar() or 0
    )

    total_chats = db.query(func.count(ChatLog.id)).scalar() or 0
    total_reviews = db.query(func.count(ToolReview.id)).scalar() or 0

    return {
        "active_users_7d": active_7d,
        "active_users_30d": active_30d,
        "total_chat_queries": total_chats,
        "total_tool_reviews": total_reviews,
    }


def get_knowledge_gap_summary(db: Session) -> dict:
    """Summary of knowledge gaps from the Brain."""
    open_gaps = (
        db.query(func.count(KnowledgeGap.id))
        .filter(KnowledgeGap.status == "open")
        .scalar() or 0
    )

    high_priority = (
        db.query(func.count(KnowledgeGap.id))
        .filter(KnowledgeGap.status == "open", KnowledgeGap.priority <= 2)
        .scalar() or 0
    )

    recent_gaps = (
        db.query(KnowledgeGap)
        .filter(KnowledgeGap.status == "open")
        .order_by(KnowledgeGap.priority.asc(), KnowledgeGap.created_at.desc())
        .limit(5)
        .all()
    )

    return {
        "open_count": open_gaps,
        "high_priority_count": high_priority,
        "recent": [
            {"topic": g.topic[:100], "priority": g.priority, "sector": g.sector}
            for g in recent_gaps
        ],
    }
