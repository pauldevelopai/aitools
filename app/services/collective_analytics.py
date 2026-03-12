"""Collective Learning analytics service.

Computes aggregated network stats from existing data across
users, tools, lessons, readiness assessments, and use cases.
Respects anonymity: omits sector data when sample_count < 3.
"""
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.discovery import DiscoveredTool
from app.models.usecase import UseCase
from app.models.lessons import LessonModule, Lesson, UserLessonProgress, UserTokens
from app.models.readiness import ReadinessAssessment
from app.models.collective_learning import NetworkInsight

logger = logging.getLogger(__name__)

# Minimum sample count for showing aggregates (anonymity)
MIN_SAMPLE_COUNT = 3


def get_network_overview(db: Session) -> dict[str, Any]:
    """High-level network stats: total users, avg readiness, top sectors."""
    total_users = db.query(sa_func.count(User.id)).scalar() or 0

    # Average readiness score
    avg_readiness = (
        db.query(sa_func.avg(ReadinessAssessment.overall_score))
        .scalar()
    )
    avg_readiness = round(float(avg_readiness), 1) if avg_readiness else None

    # Total approved tools
    total_tools = (
        db.query(sa_func.count(DiscoveredTool.id))
        .filter(DiscoveredTool.status == "approved")
        .scalar()
    ) or 0

    # Lessons completed across all users
    total_lessons_completed = (
        db.query(sa_func.count(UserLessonProgress.id))
        .filter(UserLessonProgress.status == "completed")
        .scalar()
    ) or 0

    # Top sectors by user count (from org type on User if available)
    top_sectors = []
    try:
        sector_counts = (
            db.query(
                User.organisation_type,
                sa_func.count(User.id),
            )
            .filter(User.organisation_type.isnot(None))
            .group_by(User.organisation_type)
            .order_by(sa_func.count(User.id).desc())
            .limit(5)
            .all()
        )
        top_sectors = [
            {"sector": s, "count": c}
            for s, c in sector_counts
            if c >= MIN_SAMPLE_COUNT
        ]
    except Exception:
        pass  # organisation_type may not exist on all deployments

    return {
        "total_users": total_users,
        "avg_readiness": avg_readiness,
        "total_tools": total_tools,
        "total_lessons_completed": total_lessons_completed,
        "top_sectors": top_sectors,
    }


def get_tool_adoption_stats(db: Session) -> dict[str, Any]:
    """Most popular approved tools across the network."""
    # Top tools (categories is JSONB list, so we extract first category)
    top_tools = (
        db.query(DiscoveredTool)
        .filter(DiscoveredTool.status == "approved")
        .order_by(DiscoveredTool.created_at.desc())
        .limit(10)
        .all()
    )

    tools_list = [
        {
            "name": t.name,
            "category": (t.categories[0] if t.categories else "uncategorised"),
            "url": t.url,
        }
        for t in top_tools
    ]

    # Category breakdown from JSONB categories field
    all_approved = (
        db.query(DiscoveredTool.categories)
        .filter(DiscoveredTool.status == "approved")
        .all()
    )
    cat_counts: dict[str, int] = {}
    for (cats,) in all_approved:
        if cats:
            for c in cats:
                cat_counts[c] = cat_counts.get(c, 0) + 1
        else:
            cat_counts["uncategorised"] = cat_counts.get("uncategorised", 0) + 1

    category_breakdown = sorted(
        [{"category": c, "count": n} for c, n in cat_counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )

    total_approved = (
        db.query(sa_func.count(DiscoveredTool.id))
        .filter(DiscoveredTool.status == "approved")
        .scalar()
    ) or 0

    return {
        "top_tools": tools_list,
        "category_breakdown": category_breakdown,
        "total_approved": total_approved,
    }


def get_use_case_highlights(db: Session) -> list[dict]:
    """Top published use cases across the network."""
    use_cases = (
        db.query(UseCase)
        .filter(UseCase.status == "approved")
        .order_by(UseCase.created_at.desc())
        .limit(5)
        .all()
    )

    return [
        {
            "title": uc.title,
            "description": uc.summary,
            "sector": (uc.sectors[0] if uc.sectors else None),
            "slug": uc.slug,
        }
        for uc in use_cases
    ]


def get_skill_growth_summary(db: Session) -> dict[str, Any]:
    """Aggregate lesson completion stats and token activity."""
    # Total lesson completions
    total_completed = (
        db.query(sa_func.count(UserLessonProgress.id))
        .filter(UserLessonProgress.status == "completed")
        .scalar()
    ) or 0

    # Users who have completed at least one lesson
    active_learners = (
        db.query(sa_func.count(sa_func.distinct(UserLessonProgress.user_id)))
        .filter(UserLessonProgress.status == "completed")
        .scalar()
    ) or 0

    # Average tokens earned
    avg_tokens = (
        db.query(sa_func.avg(UserTokens.total_earned))
        .scalar()
    )
    avg_tokens = round(float(avg_tokens), 1) if avg_tokens else 0

    # Most active modules (by completion count)
    popular_modules = (
        db.query(
            LessonModule.name,
            sa_func.count(UserLessonProgress.id).label("completions"),
        )
        .join(Lesson, Lesson.module_id == LessonModule.id)
        .join(UserLessonProgress, UserLessonProgress.lesson_id == Lesson.id)
        .filter(UserLessonProgress.status == "completed")
        .group_by(LessonModule.name)
        .order_by(sa_func.count(UserLessonProgress.id).desc())
        .limit(5)
        .all()
    )

    return {
        "total_completed": total_completed,
        "active_learners": active_learners,
        "avg_tokens_earned": avg_tokens,
        "popular_modules": [
            {"module": name, "completions": cnt}
            for name, cnt in popular_modules
        ],
    }


def get_sector_comparisons(db: Session) -> list[dict]:
    """Sector-level comparisons using benchmark data."""
    from app.models.benchmark import SectorBenchmarkAggregate

    aggregates = (
        db.query(SectorBenchmarkAggregate)
        .filter(
            SectorBenchmarkAggregate.country.is_(None),
            SectorBenchmarkAggregate.sample_count >= MIN_SAMPLE_COUNT,
        )
        .order_by(SectorBenchmarkAggregate.avg_stage.desc())
        .all()
    )

    return [
        {
            "sector": agg.sector,
            "avg_stage": agg.avg_stage,
            "sample_count": agg.sample_count,
        }
        for agg in aggregates
    ]


def get_dashboard_data(db: Session) -> dict[str, Any]:
    """Assemble all data needed for the collective learning dashboard."""
    return {
        "overview": get_network_overview(db),
        "tool_adoption": get_tool_adoption_stats(db),
        "use_case_highlights": get_use_case_highlights(db),
        "skill_growth": get_skill_growth_summary(db),
        "sector_comparisons": get_sector_comparisons(db),
    }
