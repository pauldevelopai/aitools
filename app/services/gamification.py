"""Gamification service — tokens, streaks, levels."""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.lessons import UserTokens, TokenTransaction, UserLessonProgress

logger = logging.getLogger(__name__)

# Level thresholds: (min_total_earned, level)
LEVEL_THRESHOLDS = [
    (0, 1),
    (6, 2),
    (16, 3),
    (31, 4),
    (51, 5),
]


def calculate_level(total_earned: int) -> int:
    """Determine level from total tokens earned."""
    level = 1
    for threshold, lvl in LEVEL_THRESHOLDS:
        if total_earned >= threshold:
            level = lvl
    return level


def get_or_create_token_record(db: Session, user_id) -> UserTokens:
    """Upsert UserTokens record for a user."""
    record = db.query(UserTokens).filter(UserTokens.user_id == user_id).first()
    if not record:
        record = UserTokens(user_id=user_id)
        db.add(record)
        db.commit()
        db.refresh(record)
    return record


def award_tokens(
    db: Session,
    user_id,
    amount: int,
    transaction_type: str,
    description: str,
    reference_id: Optional[str] = None,
) -> UserTokens:
    """Add tokens to user balance and log the transaction."""
    record = get_or_create_token_record(db, user_id)

    record.balance += amount
    record.total_earned += amount
    record.level = calculate_level(record.total_earned)
    record.updated_at = datetime.now(timezone.utc)

    tx = TokenTransaction(
        user_id=user_id,
        amount=amount,
        transaction_type=transaction_type,
        reference_id=reference_id,
        description=description,
    )
    db.add(tx)
    db.commit()
    db.refresh(record)
    logger.info(f"Awarded {amount} tokens to user {user_id} ({transaction_type})")
    return record


def update_streak(db: Session, user_id) -> UserTokens:
    """Update streak based on last_completed_at.

    Rules:
    - If no previous completion: streak = 1
    - If last completion was today: streak unchanged (idempotent)
    - If last completion was yesterday: streak += 1
    - If last completion was 2+ days ago: streak resets to 1
    """
    record = get_or_create_token_record(db, user_id)
    now = datetime.now(timezone.utc)

    if record.last_completed_at is None:
        record.current_streak = 1
    else:
        last = record.last_completed_at
        days_diff = (now.date() - last.date()).days
        if days_diff == 0:
            pass  # Already completed today, no change
        elif days_diff == 1:
            record.current_streak += 1
        else:
            record.current_streak = 1  # Reset

    if record.current_streak > record.longest_streak:
        record.longest_streak = record.current_streak

    record.last_completed_at = now
    record.updated_at = now
    db.commit()
    db.refresh(record)
    return record


def get_profile(db: Session, user_id) -> dict:
    """Return token balance, streak, level, and completion counts."""
    record = get_or_create_token_record(db, user_id)

    completed_lessons = (
        db.query(UserLessonProgress)
        .filter(
            UserLessonProgress.user_id == user_id,
            UserLessonProgress.status == "completed",
        )
        .count()
    )

    return {
        "balance": record.balance,
        "total_earned": record.total_earned,
        "current_streak": record.current_streak,
        "longest_streak": record.longest_streak,
        "level": record.level,
        "completed_lessons": completed_lessons,
    }
