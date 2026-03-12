"""Content quality tracking for the Grounded Brain.

Updates quality scores based on RAG usage, user feedback,
and content staleness. Flags content for refresh when quality drops.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.brain import ContentQualityScore

logger = logging.getLogger(__name__)

# How old content must be before staleness starts increasing
STALENESS_THRESHOLD_DAYS = 180  # 6 months


class ContentQualityTracker:
    """Tracks and updates content quality scores."""

    def __init__(self, db: Session):
        self.db = db

    def _get_or_create(self, content_type: str, content_id: str) -> ContentQualityScore:
        """Get or create a quality score record."""
        score = (
            self.db.query(ContentQualityScore)
            .filter(
                ContentQualityScore.content_type == content_type,
                ContentQualityScore.content_id == content_id,
            )
            .first()
        )
        if not score:
            score = ContentQualityScore(
                content_type=content_type,
                content_id=content_id,
            )
            self.db.add(score)
            self.db.commit()
            self.db.refresh(score)
        return score

    def record_rag_usage(
        self,
        content_type: str,
        content_id: str,
        similarity: float,
    ) -> None:
        """Record that a piece of content was used in a RAG response.

        Args:
            content_type: Type of content (chunk, tool, use_case, etc.)
            content_id: ID of the content
            similarity: Cosine similarity score when retrieved
        """
        score = self._get_or_create(content_type, content_id)

        # Update citation count
        score.times_cited += 1
        score.last_used_at = datetime.now(timezone.utc)

        # Update rolling average similarity
        if score.avg_similarity_when_used is None:
            score.avg_similarity_when_used = similarity
        else:
            # Exponential moving average (gives more weight to recent)
            alpha = 0.3
            score.avg_similarity_when_used = (
                alpha * similarity + (1 - alpha) * score.avg_similarity_when_used
            )

        self._recalculate_quality(score)
        self.db.commit()

    def record_positive_feedback(self, content_type: str, content_id: str) -> None:
        """Record positive user feedback for content."""
        score = self._get_or_create(content_type, content_id)
        score.positive_feedback_count += 1
        self._recalculate_quality(score)
        self.db.commit()

    def record_negative_feedback(self, content_type: str, content_id: str) -> None:
        """Record negative user feedback for content."""
        score = self._get_or_create(content_type, content_id)
        score.negative_feedback_count += 1
        self._recalculate_quality(score)
        self.db.commit()

    def update_staleness(self, content_type: str, content_id: str, content_created_at: datetime) -> None:
        """Update staleness score based on content age.

        Args:
            content_type: Type of content
            content_id: ID of the content
            content_created_at: When the content was originally created/updated
        """
        score = self._get_or_create(content_type, content_id)

        age_days = (datetime.now(timezone.utc) - content_created_at).days
        if age_days <= STALENESS_THRESHOLD_DAYS:
            score.staleness_score = 0.0
        else:
            # Linear increase from 0 to 1 over the next 6 months
            excess_days = age_days - STALENESS_THRESHOLD_DAYS
            score.staleness_score = min(1.0, excess_days / STALENESS_THRESHOLD_DAYS)

        self._recalculate_quality(score)
        self.db.commit()

    def _recalculate_quality(self, score: ContentQualityScore) -> None:
        """Recalculate the overall quality score.

        Composite of:
        - Feedback ratio (40% weight)
        - Similarity when used (30% weight)
        - Staleness inverse (30% weight)
        """
        # Feedback component (0-1)
        total_feedback = score.positive_feedback_count + score.negative_feedback_count
        if total_feedback > 0:
            feedback_score = score.positive_feedback_count / total_feedback
        else:
            feedback_score = 0.5  # Neutral when no feedback

        # Similarity component (0-1)
        similarity_score = score.avg_similarity_when_used or 0.5

        # Freshness component (inverse of staleness)
        freshness_score = 1.0 - score.staleness_score

        # Weighted composite
        score.overall_quality_score = round(
            0.4 * feedback_score + 0.3 * similarity_score + 0.3 * freshness_score,
            3,
        )

    def get_low_quality_content(self, threshold: float = 0.3, limit: int = 20) -> list[ContentQualityScore]:
        """Get content that has dropped below the quality threshold.

        Args:
            threshold: Quality score below which content is flagged
            limit: Maximum number of records to return

        Returns:
            List of ContentQualityScore records
        """
        return (
            self.db.query(ContentQualityScore)
            .filter(ContentQualityScore.overall_quality_score < threshold)
            .order_by(ContentQualityScore.overall_quality_score.asc())
            .limit(limit)
            .all()
        )

    def get_stale_content(self, threshold: float = 0.7, limit: int = 20) -> list[ContentQualityScore]:
        """Get content that is getting stale.

        Args:
            threshold: Staleness score above which content is flagged
            limit: Maximum number of records to return

        Returns:
            List of ContentQualityScore records
        """
        return (
            self.db.query(ContentQualityScore)
            .filter(ContentQualityScore.staleness_score >= threshold)
            .order_by(ContentQualityScore.staleness_score.desc())
            .limit(limit)
            .all()
        )

    def get_quality_stats(self) -> dict[str, Any]:
        """Get summary statistics about content quality."""
        total = self.db.query(func.count(ContentQualityScore.id)).scalar() or 0
        avg_quality = (
            self.db.query(func.avg(ContentQualityScore.overall_quality_score)).scalar()
        )
        low_quality = (
            self.db.query(func.count(ContentQualityScore.id))
            .filter(ContentQualityScore.overall_quality_score < 0.3)
            .scalar() or 0
        )
        stale = (
            self.db.query(func.count(ContentQualityScore.id))
            .filter(ContentQualityScore.staleness_score >= 0.7)
            .scalar() or 0
        )

        return {
            "total_tracked": total,
            "avg_quality_score": round(avg_quality, 3) if avg_quality else None,
            "low_quality_count": low_quality,
            "stale_count": stale,
        }
