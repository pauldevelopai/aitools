"""Knowledge gap detection for the Grounded Brain.

Monitors low-similarity RAG queries, chatbot fallback responses,
user negative feedback, and stale content to identify gaps in the
platform's knowledge base.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.brain import KnowledgeGap

logger = logging.getLogger(__name__)

# Thresholds
LOW_SIMILARITY_THRESHOLD = 0.4
STALENESS_MONTHS = 6


class KnowledgeGapDetector:
    """Detects and records knowledge gaps."""

    def __init__(self, db: Session):
        self.db = db

    def detect_low_similarity(
        self,
        query: str,
        best_similarity: float,
        sector: str | None = None,
    ) -> KnowledgeGap | None:
        """Record a gap when a RAG query has low similarity results.

        Args:
            query: The user's search query
            best_similarity: Best similarity score from the RAG search
            sector: User's sector if known

        Returns:
            Created KnowledgeGap or None if duplicate
        """
        if best_similarity >= LOW_SIMILARITY_THRESHOLD:
            return None

        # Check for existing similar gap (avoid duplicates)
        existing = (
            self.db.query(KnowledgeGap)
            .filter(
                KnowledgeGap.topic.ilike(f"%{query[:50]}%"),
                KnowledgeGap.status.in_(["open", "researching"]),
            )
            .first()
        )
        if existing:
            # Increase priority if seen again
            if existing.priority > 1:
                existing.priority -= 1
                self.db.commit()
            return None

        gap = KnowledgeGap(
            topic=query[:500],
            sector=sector,
            gap_type="no_content",
            detected_from="low_similarity",
            detection_details={
                "query": query,
                "best_similarity": round(best_similarity, 4),
                "detected_at": datetime.now(timezone.utc).isoformat(),
            },
            priority=3 if best_similarity > 0.2 else 2,
        )
        self.db.add(gap)
        self.db.commit()
        self.db.refresh(gap)

        logger.info(
            f"Knowledge gap detected: '{query[:80]}' "
            f"(similarity={best_similarity:.3f}, priority={gap.priority})"
        )
        return gap

    def detect_fallback_response(
        self,
        query: str,
        sector: str | None = None,
    ) -> KnowledgeGap | None:
        """Record a gap when the chatbot falls back to a generic response.

        Args:
            query: The user's question
            sector: User's sector if known

        Returns:
            Created KnowledgeGap or None if duplicate
        """
        existing = (
            self.db.query(KnowledgeGap)
            .filter(
                KnowledgeGap.topic.ilike(f"%{query[:50]}%"),
                KnowledgeGap.status.in_(["open", "researching"]),
            )
            .first()
        )
        if existing:
            if existing.priority > 1:
                existing.priority -= 1
                self.db.commit()
            return None

        gap = KnowledgeGap(
            topic=query[:500],
            sector=sector,
            gap_type="no_content",
            detected_from="low_similarity",
            detection_details={
                "query": query,
                "reason": "fallback_response",
                "detected_at": datetime.now(timezone.utc).isoformat(),
            },
            priority=2,  # Higher priority for total misses
        )
        self.db.add(gap)
        self.db.commit()
        self.db.refresh(gap)

        logger.info(f"Knowledge gap (fallback): '{query[:80]}' (priority=2)")
        return gap

    def detect_negative_feedback(
        self,
        query: str,
        content_id: str | None = None,
        user_id: str | None = None,
        sector: str | None = None,
    ) -> KnowledgeGap | None:
        """Record a gap from user negative feedback.

        Args:
            query: The question the user asked
            content_id: ID of the content that was shown
            user_id: ID of the user who gave feedback
            sector: User's sector if known

        Returns:
            Created KnowledgeGap or None
        """
        existing = (
            self.db.query(KnowledgeGap)
            .filter(
                KnowledgeGap.topic.ilike(f"%{query[:50]}%"),
                KnowledgeGap.status.in_(["open", "researching"]),
            )
            .first()
        )
        if existing:
            if existing.priority > 1:
                existing.priority -= 1
                self.db.commit()
            return None

        gap = KnowledgeGap(
            topic=query[:500],
            sector=sector,
            gap_type="low_quality" if content_id else "no_content",
            detected_from="user_feedback",
            detection_details={
                "query": query,
                "content_id": content_id,
                "user_id": user_id,
                "detected_at": datetime.now(timezone.utc).isoformat(),
            },
            priority=2,
        )
        self.db.add(gap)
        self.db.commit()
        self.db.refresh(gap)

        logger.info(f"Knowledge gap (feedback): '{query[:80]}' (priority=2)")
        return gap

    def get_top_gaps(self, limit: int = 10, sector: str | None = None) -> list[KnowledgeGap]:
        """Get the highest priority open knowledge gaps.

        Args:
            limit: Maximum number of gaps to return
            sector: Filter by sector if provided

        Returns:
            List of KnowledgeGap records ordered by priority
        """
        query = (
            self.db.query(KnowledgeGap)
            .filter(KnowledgeGap.status == "open")
            .order_by(KnowledgeGap.priority.asc(), KnowledgeGap.created_at.asc())
        )
        if sector:
            query = query.filter(
                (KnowledgeGap.sector == sector) | (KnowledgeGap.sector.is_(None))
            )
        return query.limit(limit).all()

    def mark_researching(self, gap_id: str, run_id: str) -> None:
        """Mark a gap as being researched by a Brain run."""
        gap = self.db.query(KnowledgeGap).filter(KnowledgeGap.id == gap_id).first()
        if gap:
            gap.status = "researching"
            gap.filled_by_run_id = run_id
            self.db.commit()

    def mark_filled(self, gap_id: str, content_id: str) -> None:
        """Mark a gap as filled after content was created."""
        gap = self.db.query(KnowledgeGap).filter(KnowledgeGap.id == gap_id).first()
        if gap:
            gap.status = "filled"
            gap.filled_by_content_id = content_id
            self.db.commit()

    def dismiss(self, gap_id: str) -> None:
        """Dismiss a gap (admin decided it's not worth filling)."""
        gap = self.db.query(KnowledgeGap).filter(KnowledgeGap.id == gap_id).first()
        if gap:
            gap.status = "dismissed"
            self.db.commit()

    def get_gap_stats(self) -> dict[str, Any]:
        """Get summary statistics about knowledge gaps."""
        total = self.db.query(func.count(KnowledgeGap.id)).scalar() or 0
        open_gaps = (
            self.db.query(func.count(KnowledgeGap.id))
            .filter(KnowledgeGap.status == "open")
            .scalar() or 0
        )
        researching = (
            self.db.query(func.count(KnowledgeGap.id))
            .filter(KnowledgeGap.status == "researching")
            .scalar() or 0
        )
        filled = (
            self.db.query(func.count(KnowledgeGap.id))
            .filter(KnowledgeGap.status == "filled")
            .scalar() or 0
        )

        # Priority breakdown for open gaps
        high_priority = (
            self.db.query(func.count(KnowledgeGap.id))
            .filter(KnowledgeGap.status == "open", KnowledgeGap.priority <= 2)
            .scalar() or 0
        )

        return {
            "total": total,
            "open": open_gaps,
            "researching": researching,
            "filled": filled,
            "high_priority_open": high_priority,
        }
