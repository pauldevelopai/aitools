"""Benchmarking service.

Calculates adoption stage from readiness + progress data,
compares against anonymous sector/global aggregates.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.models.benchmark import OrgBenchmark, SectorBenchmarkAggregate
from app.models.readiness import ReadinessAssessment
from app.models.progress import UserProgress
from app.models.auth import User
from app.services.progress_tracker import refresh_progress

logger = logging.getLogger(__name__)

# Minimum sample count for showing aggregates (anonymity)
MIN_SAMPLE_COUNT = 3

# Dimension defaults when no readiness assessment exists
DEFAULT_DIMENSIONS = {
    "awareness": 1.0,
    "policy": 1.0,
    "tools": 1.0,
    "governance": 1.0,
    "skills": 1.0,
}


def calculate_adoption_stage(db: Session, user_id) -> tuple[float, dict]:
    """Calculate a user's adoption stage (1.0-5.0).

    Derives from:
    - Readiness assessment scores (60% weight if available)
    - Progress completion percentage (40% weight)

    Returns:
        (adoption_stage, dimension_scores)
    """
    # Get readiness scores if available
    assessment = (
        db.query(ReadinessAssessment)
        .filter(ReadinessAssessment.user_id == user_id)
        .order_by(ReadinessAssessment.created_at.desc())
        .first()
    )

    if assessment and assessment.dimension_scores:
        dimension_scores = dict(assessment.dimension_scores)
        readiness_score = assessment.overall_score
    else:
        dimension_scores = dict(DEFAULT_DIMENSIONS)
        readiness_score = 1.0

    # Get progress completion
    progress = refresh_progress(db, user_id)
    progress_pct = progress.overall_completion_pct / 100.0  # 0-1

    # Convert progress to 1-5 scale
    progress_score = 1.0 + (progress_pct * 4.0)

    # Weighted combination
    if assessment:
        adoption_stage = round(0.6 * readiness_score + 0.4 * progress_score, 2)
    else:
        # Without assessment, rely more on progress
        adoption_stage = round(progress_score, 2)

    # Clamp to 1.0-5.0
    adoption_stage = max(1.0, min(5.0, adoption_stage))

    return adoption_stage, dimension_scores


def get_or_update_benchmark(db: Session, user_id) -> OrgBenchmark:
    """Get or recalculate a user's benchmark record."""
    user = db.query(User).filter(User.id == user_id).first()

    adoption_stage, dimension_scores = calculate_adoption_stage(db, user_id)

    # Upsert benchmark
    benchmark = (
        db.query(OrgBenchmark)
        .filter(OrgBenchmark.user_id == user_id)
        .first()
    )

    if benchmark:
        benchmark.adoption_stage = adoption_stage
        benchmark.dimension_scores = dimension_scores
        benchmark.sector = getattr(user, "organisation_type", None)
        benchmark.country = getattr(user, "country", None)
        benchmark.calculated_at = datetime.now(timezone.utc)
    else:
        benchmark = OrgBenchmark(
            user_id=user_id,
            adoption_stage=adoption_stage,
            dimension_scores=dimension_scores,
            sector=getattr(user, "organisation_type", None),
            country=getattr(user, "country", None),
        )
        db.add(benchmark)

    db.commit()
    db.refresh(benchmark)
    return benchmark


def get_peer_comparison(db: Session, user_id) -> dict[str, Any]:
    """Get a user's benchmark position vs sector and global averages.

    Returns:
        {
            "user_stage": float,
            "user_dimensions": dict,
            "sector": str | None,
            "sector_avg": float | None,
            "sector_dimensions": dict | None,
            "sector_sample": int,
            "global_avg": float | None,
            "global_dimensions": dict | None,
            "global_sample": int,
            "insights": list[str],
        }
    """
    benchmark = get_or_update_benchmark(db, user_id)

    result = {
        "user_stage": benchmark.adoption_stage,
        "user_dimensions": benchmark.dimension_scores or {},
        "sector": benchmark.sector,
        "sector_avg": None,
        "sector_dimensions": None,
        "sector_sample": 0,
        "global_avg": None,
        "global_dimensions": None,
        "global_sample": 0,
        "insights": [],
    }

    # Sector average (global aggregate for sector, country=None)
    if benchmark.sector:
        sector_agg = (
            db.query(SectorBenchmarkAggregate)
            .filter(
                SectorBenchmarkAggregate.sector == benchmark.sector,
                SectorBenchmarkAggregate.country.is_(None),
            )
            .order_by(SectorBenchmarkAggregate.calculated_at.desc())
            .first()
        )
        if sector_agg and sector_agg.sample_count >= MIN_SAMPLE_COUNT:
            result["sector_avg"] = sector_agg.avg_stage
            result["sector_dimensions"] = sector_agg.dimension_averages
            result["sector_sample"] = sector_agg.sample_count

    # Global average (all sectors combined — compute on the fly)
    global_stats = (
        db.query(
            sa_func.avg(OrgBenchmark.adoption_stage),
            sa_func.count(OrgBenchmark.id),
        )
        .first()
    )
    if global_stats and global_stats[1] >= MIN_SAMPLE_COUNT:
        result["global_avg"] = round(float(global_stats[0]), 2)
        result["global_sample"] = global_stats[1]

        # Compute global dimension averages
        all_benchmarks = db.query(OrgBenchmark.dimension_scores).all()
        if all_benchmarks:
            dim_totals: dict[str, float] = {}
            dim_counts: dict[str, int] = {}
            for (dims,) in all_benchmarks:
                if dims:
                    for k, v in dims.items():
                        dim_totals[k] = dim_totals.get(k, 0.0) + float(v)
                        dim_counts[k] = dim_counts.get(k, 0) + 1
            result["global_dimensions"] = {
                k: round(dim_totals[k] / dim_counts[k], 2)
                for k in dim_totals
            }

    # Generate insights
    result["insights"] = _generate_insights(result)

    return result


def _generate_insights(comparison: dict) -> list[str]:
    """Generate human-readable insight strings from comparison data."""
    insights = []
    user_dims = comparison.get("user_dimensions", {})

    # Compare vs sector
    sector_dims = comparison.get("sector_dimensions")
    if sector_dims and comparison.get("sector"):
        sector_name = comparison["sector"].replace("_", " ").title()
        ahead = []
        behind = []
        for dim in user_dims:
            if dim in sector_dims:
                diff = user_dims[dim] - sector_dims[dim]
                if diff > 0.3:
                    ahead.append(dim.title())
                elif diff < -0.3:
                    behind.append(dim.title())
        if ahead:
            insights.append(f"You're ahead of similar {sector_name} organisations in: {', '.join(ahead)}")
        if behind:
            insights.append(f"Room to grow compared to peers in: {', '.join(behind)}")

    # Stage insight
    if comparison.get("sector_avg") is not None:
        diff = comparison["user_stage"] - comparison["sector_avg"]
        if diff > 0.5:
            insights.append("Your adoption stage is above the sector average")
        elif diff < -0.5:
            insights.append("Your adoption stage is below the sector average — the platform can help you catch up")

    if not insights:
        insights.append("Complete your readiness assessment and build your policies to see how you compare")

    return insights


def recalculate_aggregates(db: Session) -> int:
    """Recompute sector benchmark aggregates from all OrgBenchmark records.

    Should be run periodically (e.g., daily). Only creates aggregates
    for sectors with at least MIN_SAMPLE_COUNT records.

    Returns:
        Number of aggregates created/updated.
    """
    # Get all sector + country combinations
    sector_groups = (
        db.query(
            OrgBenchmark.sector,
            sa_func.avg(OrgBenchmark.adoption_stage),
            sa_func.count(OrgBenchmark.id),
        )
        .filter(OrgBenchmark.sector.isnot(None))
        .group_by(OrgBenchmark.sector)
        .all()
    )

    count = 0
    for sector, avg_stage, sample_count in sector_groups:
        if sample_count < MIN_SAMPLE_COUNT:
            continue

        # Calculate median
        stages = (
            db.query(OrgBenchmark.adoption_stage)
            .filter(OrgBenchmark.sector == sector)
            .order_by(OrgBenchmark.adoption_stage)
            .all()
        )
        stages_list = [s[0] for s in stages]
        mid = len(stages_list) // 2
        median = stages_list[mid] if len(stages_list) % 2 else (stages_list[mid - 1] + stages_list[mid]) / 2

        # Dimension averages
        benchmarks = (
            db.query(OrgBenchmark.dimension_scores)
            .filter(OrgBenchmark.sector == sector)
            .all()
        )
        dim_totals: dict[str, float] = {}
        dim_counts: dict[str, int] = {}
        for (dims,) in benchmarks:
            if dims:
                for k, v in dims.items():
                    dim_totals[k] = dim_totals.get(k, 0.0) + float(v)
                    dim_counts[k] = dim_counts.get(k, 0) + 1
        dimension_averages = {
            k: round(dim_totals[k] / dim_counts[k], 2)
            for k in dim_totals
        }

        # Upsert aggregate (global = country is None)
        agg = (
            db.query(SectorBenchmarkAggregate)
            .filter(
                SectorBenchmarkAggregate.sector == sector,
                SectorBenchmarkAggregate.country.is_(None),
            )
            .first()
        )
        if agg:
            agg.avg_stage = round(float(avg_stage), 2)
            agg.median_stage = round(float(median), 2)
            agg.sample_count = sample_count
            agg.dimension_averages = dimension_averages
            agg.calculated_at = datetime.now(timezone.utc)
        else:
            agg = SectorBenchmarkAggregate(
                sector=sector,
                country=None,
                avg_stage=round(float(avg_stage), 2),
                median_stage=round(float(median), 2),
                sample_count=sample_count,
                dimension_averages=dimension_averages,
            )
            db.add(agg)
        count += 1

    db.commit()
    logger.info(f"Recalculated {count} sector benchmark aggregates")
    return count
