"""Audit Rubric scoring service.

Manages interactive scoring of tools across the 4 audit dimensions:
Data Sovereignty, Exportability, Business Model, Security.
"""
import logging
from typing import Any, Optional
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.models.enhancements import AuditScore

logger = logging.getLogger(__name__)

DIMENSIONS = [
    {
        "key": "data_sovereignty",
        "label": "Data Sovereignty",
        "description": "Who controls data, where it is processed, which laws apply, and who can access it.",
        "zero_label": "No sovereignty — data uploaded, stored, logged, reused for training",
        "five_label": "Full sovereignty — local processing, user controls storage and deletion",
    },
    {
        "key": "exportability",
        "label": "Exportability",
        "description": "The ability to retrieve, move and reuse your data without lock-in.",
        "zero_label": "No exportability — data locked in proprietary interface",
        "five_label": "Full exportability — all data exportable instantly, no restrictions",
    },
    {
        "key": "business_model",
        "label": "Business Model",
        "description": "How the company makes money and whether your data is part of the product.",
        "zero_label": "Extractive — vague ToS, data used for training/resale",
        "five_label": "Aligned & transparent — clear pricing, no data monetisation",
    },
    {
        "key": "security",
        "label": "Security",
        "description": "How the tool protects your accounts, content and access from others.",
        "zero_label": "Insecure — single password, no encryption, weak access controls",
        "five_label": "Strong security — E2EE, access control, logging, recovery",
    },
]


def score_tool(
    db: Session,
    user_id: str,
    tool_slug: str,
    data_sovereignty: int,
    exportability: int,
    business_model: int,
    security: int,
    notes: Optional[str] = None,
) -> AuditScore:
    """Create or update an audit score for a tool."""
    total = data_sovereignty + exportability + business_model + security

    existing = db.query(AuditScore).filter(
        AuditScore.user_id == user_id,
        AuditScore.tool_slug == tool_slug,
    ).first()

    if existing:
        existing.data_sovereignty = data_sovereignty
        existing.exportability = exportability
        existing.business_model = business_model
        existing.security = security
        existing.total_score = total
        existing.notes = notes
        db.commit()
        db.refresh(existing)
        return existing

    score = AuditScore(
        user_id=user_id,
        tool_slug=tool_slug,
        data_sovereignty=data_sovereignty,
        exportability=exportability,
        business_model=business_model,
        security=security,
        total_score=total,
        notes=notes,
    )
    db.add(score)
    db.commit()
    db.refresh(score)
    return score


def get_user_scores(db: Session, user_id: str) -> list[AuditScore]:
    """Get all audit scores for a user."""
    return db.query(AuditScore).filter(
        AuditScore.user_id == user_id
    ).order_by(AuditScore.updated_at.desc()).all()


def get_user_score_for_tool(
    db: Session, user_id: str, tool_slug: str
) -> Optional[AuditScore]:
    """Get a user's audit score for a specific tool."""
    return db.query(AuditScore).filter(
        AuditScore.user_id == user_id,
        AuditScore.tool_slug == tool_slug,
    ).first()


def get_tool_aggregate(db: Session, tool_slug: str) -> dict[str, Any]:
    """Get average audit scores for a tool across all users."""
    result = db.query(
        sa_func.count(AuditScore.id).label("count"),
        sa_func.avg(AuditScore.data_sovereignty).label("avg_sovereignty"),
        sa_func.avg(AuditScore.exportability).label("avg_exportability"),
        sa_func.avg(AuditScore.business_model).label("avg_business_model"),
        sa_func.avg(AuditScore.security).label("avg_security"),
        sa_func.avg(AuditScore.total_score).label("avg_total"),
    ).filter(
        AuditScore.tool_slug == tool_slug
    ).first()

    if not result or result.count == 0:
        return {"count": 0}

    return {
        "count": result.count,
        "avg_sovereignty": round(float(result.avg_sovereignty), 1),
        "avg_exportability": round(float(result.avg_exportability), 1),
        "avg_business_model": round(float(result.avg_business_model), 1),
        "avg_security": round(float(result.avg_security), 1),
        "avg_total": round(float(result.avg_total), 1),
    }


def get_all_aggregates(db: Session) -> list[dict[str, Any]]:
    """Get aggregated audit scores for all tools that have been scored."""
    results = db.query(
        AuditScore.tool_slug,
        sa_func.count(AuditScore.id).label("count"),
        sa_func.avg(AuditScore.total_score).label("avg_total"),
        sa_func.avg(AuditScore.data_sovereignty).label("avg_sovereignty"),
        sa_func.avg(AuditScore.exportability).label("avg_exportability"),
        sa_func.avg(AuditScore.business_model).label("avg_business_model"),
        sa_func.avg(AuditScore.security).label("avg_security"),
    ).group_by(AuditScore.tool_slug).order_by(
        sa_func.avg(AuditScore.total_score).desc()
    ).all()

    return [
        {
            "tool_slug": r.tool_slug,
            "count": r.count,
            "avg_total": round(float(r.avg_total), 1),
            "avg_sovereignty": round(float(r.avg_sovereignty), 1),
            "avg_exportability": round(float(r.avg_exportability), 1),
            "avg_business_model": round(float(r.avg_business_model), 1),
            "avg_security": round(float(r.avg_security), 1),
        }
        for r in results
    ]
