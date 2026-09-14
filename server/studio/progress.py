"""Dashboard summaries derived from recorded sessions, never simulated progress."""

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import TrainingSession, User


def dashboard_progress(
    db: Session, user: User, answers: dict | None, now: datetime | None = None
) -> dict:
    answers = answers or {}
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        raise ValueError("now must contain a timezone")
    try:
        zone = ZoneInfo(answers.get("timezone") or "UTC")
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        # Legacy profiles may predate strict IANA timezone validation.
        zone = ZoneInfo("UTC")
    local_now = now.astimezone(zone)
    sunday = local_now.date() - timedelta(days=(local_now.weekday() + 1) % 7)
    start = datetime.combine(sunday, time.min, tzinfo=zone)
    end = datetime.combine(sunday + timedelta(days=7), time.min, tzinfo=zone)
    minutes = answers.get("minutes", 0)
    days = answers.get("days", [])
    target = minutes * len(set(days))

    # Filter in PostgreSQL so unrelated users and historical sessions never load.
    completed, count = db.execute(
        select(func.coalesce(func.sum(TrainingSession.actual_minutes), 0), func.count()).where(
            TrainingSession.user_id == user.id,
            TrainingSession.status == "completed",
            TrainingSession.completed_at >= start,
            TrainingSession.completed_at < end,
            TrainingSession.completed_at <= now,
            TrainingSession.actual_minutes.is_not(None),
        )
    ).one()
    next_session = db.scalar(
        select(TrainingSession)
        .where(
            TrainingSession.user_id == user.id,
            TrainingSession.status == "planned",
            TrainingSession.scheduled_at >= now,
        )
        .order_by(TrainingSession.scheduled_at, TrainingSession.id)
        .limit(1)
    )
    return {
        "session_minutes": minutes,
        "target_minutes": target,
        "completed_minutes": completed,
        "completed_sessions": count,
        "progress_percent": min(100, round(completed / target * 100, 1)) if target else 0,
        "timezone": zone.key,
        "week_start": start.isoformat(),
        "week_end": end.isoformat(),
        "next_session": {
            "id": str(next_session.id),
            "title": next_session.title,
            "goal": next_session.goal,
            "scheduled_at": next_session.scheduled_at.astimezone(zone).isoformat(),
        }
        if next_session
        else None,
    }
