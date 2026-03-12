"""Micro-lessons service — modules, lessons, progress, and AI review."""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.lessons import LessonModule, Lesson, UserLessonProgress
from app.services.gamification import award_tokens, update_streak, get_or_create_token_record

logger = logging.getLogger(__name__)


def get_modules_for_user(db: Session, user=None) -> list[dict]:
    """Return all active modules ordered by `order`, with unlock status.

    Uses level-aware unlock logic:
    - Advanced users: everything unlocked
    - Intermediate users: beginner + intermediate unlocked from start
    - Beginner users: beginner modules unlocked from start
    - All users: must complete prerequisite modules for higher-level content
    - No ai_experience_level: falls back to sequential unlock
    """
    modules = (
        db.query(LessonModule)
        .filter(LessonModule.is_active == True)
        .order_by(LessonModule.order)
        .all()
    )

    result = []
    for i, module in enumerate(modules):
        # First module always unlocked
        if i == 0:
            unlocked = True
        elif user is None:
            unlocked = False
        else:
            unlocked = is_module_unlocked(db, user.id, module, user=user)

        # Count completed lessons
        published = _get_published_lessons(db, module.id)
        if user and published:
            lesson_ids = [l.id for l in published]
            completed_count = (
                db.query(UserLessonProgress)
                .filter(
                    UserLessonProgress.user_id == user.id,
                    UserLessonProgress.lesson_id.in_(lesson_ids),
                    UserLessonProgress.status == "completed",
                )
                .count()
            )
        else:
            completed_count = 0

        # Recommendation scoring
        is_recommended = _is_module_recommended(module, user) if user else False

        result.append({
            "module": module,
            "unlocked": unlocked,
            "completed_count": completed_count,
            "total_count": len(published),
            "is_recommended": is_recommended,
        })

    return result


def is_module_unlocked(db: Session, user_id, module: LessonModule, user=None) -> bool:
    """A module is unlocked based on user level + prerequisite completion.

    Rules:
    - Advanced users: everything unlocked
    - Intermediate users: beginner + intermediate unlocked from start
    - Beginner users: beginner modules unlocked from start
    - Prerequisite modules (JSONB) must be completed for non-level-unlocked content
    - No ai_experience_level set: fall back to sequential (original behavior)
    """
    # Level-based fast unlock
    user_level = getattr(user, "ai_experience_level", None) if user else None

    if user_level == "advanced":
        return True

    if user_level == "intermediate" and module.difficulty in ("beginner", "intermediate"):
        return True

    if user_level == "beginner" and module.difficulty == "beginner":
        return True

    # Check explicit prerequisites (new JSONB field)
    prerequisites = module.prerequisites or []
    if prerequisites:
        for prereq_slug in prerequisites:
            prereq_module = (
                db.query(LessonModule)
                .filter(LessonModule.slug == prereq_slug, LessonModule.is_active == True)
                .first()
            )
            if not prereq_module:
                continue  # Skip missing modules
            if not _all_lessons_completed(db, user_id, prereq_module.id):
                return False
        return True

    # Fall back to sequential unlock (original behavior for modules without prerequisites)
    prev_module = (
        db.query(LessonModule)
        .filter(
            LessonModule.order < module.order,
            LessonModule.is_active == True,
        )
        .order_by(LessonModule.order.desc())
        .first()
    )
    if not prev_module:
        return True  # No previous module — first one

    return _all_lessons_completed(db, user_id, prev_module.id)


def _all_lessons_completed(db: Session, user_id, module_id) -> bool:
    """Check if all published lessons in a module are completed by the user."""
    published = _get_published_lessons(db, module_id)
    if not published:
        return True
    lesson_ids = [l.id for l in published]
    completed_count = (
        db.query(UserLessonProgress)
        .filter(
            UserLessonProgress.user_id == user_id,
            UserLessonProgress.lesson_id.in_(lesson_ids),
            UserLessonProgress.status == "completed",
        )
        .count()
    )
    return completed_count >= len(published)


def _is_module_recommended(module: LessonModule, user) -> bool:
    """Score whether this module is a good recommendation for the user.

    Returns True if module difficulty matches user's AI experience level.
    """
    user_level = getattr(user, "ai_experience_level", None)
    if not user_level:
        return False

    # Exact match is best recommendation
    if module.difficulty == user_level:
        return True

    # Intermediate users also recommended beginner content they haven't started
    if user_level == "intermediate" and module.difficulty == "beginner":
        return False  # They should be past this

    return False


def _get_published_lessons(db: Session, module_id) -> list[Lesson]:
    """Get published lessons for a module, ordered."""
    return (
        db.query(Lesson)
        .filter(Lesson.module_id == module_id, Lesson.status == "published")
        .order_by(Lesson.order)
        .all()
    )


def get_module_by_slug(db: Session, slug: str) -> Optional[LessonModule]:
    """Fetch an active module by slug."""
    return (
        db.query(LessonModule)
        .filter(LessonModule.slug == slug, LessonModule.is_active == True)
        .first()
    )


def get_lesson_by_slugs(db: Session, module_slug: str, lesson_slug: str) -> Optional[Lesson]:
    """Fetch a lesson by its module slug and lesson slug."""
    module = get_module_by_slug(db, module_slug)
    if not module:
        return None
    return (
        db.query(Lesson)
        .filter(Lesson.module_id == module.id, Lesson.slug == lesson_slug)
        .first()
    )


def get_user_lesson_progress(db: Session, user_id, module_id) -> dict:
    """Return a dict keyed by lesson_id string for quick lookup in templates."""
    lesson_ids = [l.id for l in _get_published_lessons(db, module_id)]
    if not lesson_ids:
        return {}
    records = (
        db.query(UserLessonProgress)
        .filter(
            UserLessonProgress.user_id == user_id,
            UserLessonProgress.lesson_id.in_(lesson_ids),
        )
        .all()
    )
    return {str(r.lesson_id): r for r in records}


def start_lesson(db: Session, user_id, lesson_id) -> UserLessonProgress:
    """Create or return existing UserLessonProgress (idempotent)."""
    existing = (
        db.query(UserLessonProgress)
        .filter(
            UserLessonProgress.user_id == user_id,
            UserLessonProgress.lesson_id == lesson_id,
        )
        .first()
    )
    if existing:
        return existing

    progress = UserLessonProgress(user_id=user_id, lesson_id=lesson_id, status="started")
    db.add(progress)
    db.commit()
    db.refresh(progress)
    return progress


def complete_lesson(
    db: Session,
    user_id,
    lesson_id,
    task_response: Optional[str] = None,
) -> dict:
    """Complete a lesson, run AI review if needed, award tokens.

    Returns a dict with: status, feedback, tokens_awarded, token_balance,
    streak, level.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        return {"error": "Lesson not found"}

    progress = start_lesson(db, user_id, lesson_id)
    if progress.status == "completed":
        # Idempotent — already done
        tokens_record = get_or_create_token_record(db, user_id)
        return {
            "status": "already_completed",
            "feedback": progress.ai_feedback,
            "tokens_awarded": 0,
            "token_balance": tokens_record.balance,
            "streak": tokens_record.current_streak,
            "level": tokens_record.level,
        }

    ai_feedback = None
    if lesson.verification_type == "ai_review" and task_response:
        ai_feedback = _get_ai_review(lesson, task_response)

    # Mark complete
    progress.status = "completed"
    progress.task_response = task_response
    progress.ai_feedback = ai_feedback
    progress.tokens_awarded = lesson.token_reward
    progress.completed_at = datetime.now(timezone.utc)
    db.commit()

    # Award tokens
    tokens_record = award_tokens(
        db,
        user_id=user_id,
        amount=lesson.token_reward,
        transaction_type="lesson_complete",
        reference_id=str(lesson_id),
        description=f"Completed: {lesson.title}",
    )

    # Update streak
    tokens_record = update_streak(db, user_id)

    # Streak bonus (every 3 days = +1 bonus token)
    if tokens_record.current_streak > 0 and tokens_record.current_streak % 3 == 0:
        tokens_record = award_tokens(
            db,
            user_id=user_id,
            amount=1,
            transaction_type="streak_bonus",
            description=f"{tokens_record.current_streak}-day streak bonus",
        )

    # Module completion bonus
    module = db.query(LessonModule).filter(LessonModule.id == lesson.module_id).first()
    if module and _check_module_just_completed(db, user_id, module.id):
        tokens_record = award_tokens(
            db,
            user_id=user_id,
            amount=3,
            transaction_type="module_complete",
            reference_id=str(module.id),
            description=f"Completed module: {module.name}",
        )

    return {
        "status": "completed",
        "feedback": ai_feedback,
        "tokens_awarded": lesson.token_reward,
        "token_balance": tokens_record.balance,
        "streak": tokens_record.current_streak,
        "level": tokens_record.level,
    }


def _check_module_just_completed(db: Session, user_id, module_id) -> bool:
    """True if all published lessons in the module are now complete."""
    published = _get_published_lessons(db, module_id)
    if not published:
        return False
    lesson_ids = [l.id for l in published]
    completed_count = (
        db.query(UserLessonProgress)
        .filter(
            UserLessonProgress.user_id == user_id,
            UserLessonProgress.lesson_id.in_(lesson_ids),
            UserLessonProgress.status == "completed",
        )
        .count()
    )
    return completed_count == len(published)


def _get_ai_review(lesson: Lesson, task_response: str) -> str:
    """Call Claude to review a user's task response.

    Returns feedback text, or a fallback message on failure.
    """
    try:
        from app.services.completion import get_completion_client

        client = get_completion_client()
        system_prompt = (
            "You are a supportive AI learning coach reviewing a user's response to a practical task. "
            "Be encouraging but specific. Acknowledge what they did well, then give one clear "
            "suggestion for how they could deepen their thinking or improve their approach. "
            "Keep feedback to 3-4 sentences maximum. Do not score or grade."
        )
        user_message = (
            f"Lesson: {lesson.title}\n\n"
            f"Task: {lesson.task_prompt}\n\n"
            f"User's response:\n{task_response}"
        )
        response = client.create_message(
            messages=[{"role": "user", "content": user_message}],
            system=system_prompt,
            max_tokens=300,
            temperature=0.4,
        )
        return response.content[0].text
    except Exception as e:
        logger.error(f"AI review failed for lesson {lesson.id}: {e}")
        return "Well done for completing this task. Your response has been saved."


# ---- Cross-reference helpers ----

def get_related_apps_for_lesson(db: Session, lesson) -> list[dict]:
    """Fetch app dicts for a lesson's related_app_slugs."""
    slugs = lesson.related_app_slugs or []
    if not slugs:
        return []
    from app.services.open_source_apps import get_apps_by_slugs
    return get_apps_by_slugs(db, slugs)


def get_lessons_for_app(db: Session, app_slug: str) -> list[dict]:
    """Find published lessons that reference a given app slug."""
    from sqlalchemy import type_coerce
    from sqlalchemy.dialects.postgresql import JSONB as JSONB_TYPE

    lessons = (
        db.query(Lesson)
        .filter(
            Lesson.status == "published",
            Lesson.related_app_slugs.op("@>")(type_coerce([app_slug], JSONB_TYPE)),
        )
        .order_by(Lesson.order)
        .all()
    )
    result = []
    for lesson in lessons:
        module = db.query(LessonModule).filter(LessonModule.id == lesson.module_id).first()
        if module:
            result.append({
                "lesson": lesson,
                "module": module,
            })
    return result
