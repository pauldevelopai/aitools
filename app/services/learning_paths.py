"""Learning paths service."""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func

from app.models.learning_path import LearningPath, UserPathEnrollment

logger = logging.getLogger(__name__)


def get_paths_for_user(db: Session, user_sector: Optional[str] = None) -> list[LearningPath]:
    """Get available learning paths, prioritising the user's sector."""
    query = db.query(LearningPath).filter(LearningPath.is_active == True)

    if user_sector:
        # Sector-matched first, then general paths
        paths = query.order_by(
            (LearningPath.sector == user_sector).desc(),
            LearningPath.name,
        ).all()
    else:
        paths = query.order_by(LearningPath.name).all()

    return paths


def get_enrollment(db: Session, user_id, path_id) -> Optional[UserPathEnrollment]:
    """Get a user's enrollment in a specific path."""
    return (
        db.query(UserPathEnrollment)
        .filter(
            UserPathEnrollment.user_id == user_id,
            UserPathEnrollment.path_id == path_id,
        )
        .first()
    )


def get_user_enrollments(db: Session, user_id) -> list[UserPathEnrollment]:
    """Get all enrollments for a user."""
    return (
        db.query(UserPathEnrollment)
        .filter(UserPathEnrollment.user_id == user_id)
        .all()
    )


def enroll_user(db: Session, user_id, path_id) -> UserPathEnrollment:
    """Enroll a user in a learning path."""
    existing = get_enrollment(db, user_id, path_id)
    if existing:
        return existing

    enrollment = UserPathEnrollment(user_id=user_id, path_id=path_id)
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment


def mark_step_complete(db: Session, user_id, path_id, step_id: str) -> Optional[UserPathEnrollment]:
    """Mark a step as complete and update completion percentage."""
    enrollment = get_enrollment(db, user_id, path_id)
    if not enrollment:
        return None

    path = db.query(LearningPath).filter(LearningPath.id == path_id).first()
    if not path:
        return None

    completed = list(enrollment.completed_steps or [])
    if step_id not in completed:
        completed.append(step_id)
        enrollment.completed_steps = completed

        # Calculate completion percentage
        total_steps = len(path.steps) if path.steps else 1
        enrollment.completion_pct = round((len(completed) / total_steps) * 100, 1)

        # Mark as fully completed if all steps done
        if len(completed) >= total_steps:
            enrollment.completed_at = datetime.now(timezone.utc)

        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(enrollment, "completed_steps")
        db.commit()
        db.refresh(enrollment)

    return enrollment


def get_path_by_slug(db: Session, slug: str) -> Optional[LearningPath]:
    """Get a learning path by its slug."""
    return (
        db.query(LearningPath)
        .filter(LearningPath.slug == slug, LearningPath.is_active == True)
        .first()
    )
