"""Weekly summaries preserve history and respect each student's local Sunday."""

from datetime import UTC, datetime, timedelta

import pytest

from studio.models import TrainingSession, User
from studio.progress import dashboard_progress


def workout(user, completed_at, minutes=60, **fields):
    return TrainingSession(
        user_id=user.id,
        title="Training",
        status="completed",
        completed_at=completed_at,
        actual_minutes=minutes,
        **fields,
    )


@pytest.mark.postgres
def test_empty_dashboard_does_not_invent_progress_or_next_training(db_factory, answers):
    with db_factory() as db:
        user = User(name="Empty")
        db.add(user)
        db.flush()
        result = dashboard_progress(db, user, answers)
        assert result["target_minutes"] == 90
        assert result["completed_minutes"] == result["progress_percent"] == 0
        assert result["next_session"] is None
        assert dashboard_progress(db, user, None)["target_minutes"] == 0


@pytest.mark.postgres
def test_week_uses_local_sunday_excludes_other_users_and_future(db_factory, answers):
    # Kyiv is UTC+3 here: its Sunday starts on Saturday at 21:00 UTC.
    start = datetime(2026, 9, 12, 21, tzinfo=UTC)
    now = start + timedelta(hours=4)
    with db_factory() as db:
        user, other = User(name="Student"), User(name="Other")
        db.add_all([user, other])
        db.flush()
        db.add_all(
            [
                workout(user, start - timedelta(microseconds=1)),
                workout(user, start, 30),
                workout(user, now, 45),
                workout(user, now + timedelta(seconds=1)),
                workout(user, start + timedelta(days=7)),
                workout(other, now),
            ]
        )
        db.flush()
        result = dashboard_progress(db, user, answers, now)
        assert result["completed_minutes"] == 75
        assert result["completed_sessions"] == 2
        assert result["progress_percent"] == 83.3
        assert result["week_start"] == "2026-09-13T00:00:00+03:00"
        assert result["week_end"] == "2026-09-20T00:00:00+03:00"
        assert db.query(TrainingSession).count() == 6


@pytest.mark.postgres
def test_dst_boundary_and_next_session_use_real_owner_schedule(db_factory, answers):
    answers = {**answers, "timezone": "Europe/Dublin"}
    now = datetime(2026, 10, 25, 12, tzinfo=UTC)
    with db_factory() as db:
        user, other = User(name="Student"), User(name="Other")
        db.add_all([user, other])
        db.flush()
        next_training = TrainingSession(
            user_id=user.id,
            title="Mobility",
            goal="mobility",
            status="planned",
            scheduled_at=now + timedelta(days=1),
        )
        db.add_all(
            [
                workout(user, now, 120),
                next_training,
                TrainingSession(
                    user_id=other.id, title="Private", status="planned", scheduled_at=now
                ),
                TrainingSession(
                    user_id=user.id,
                    title="Past",
                    status="planned",
                    scheduled_at=now - timedelta(days=1),
                ),
            ]
        )
        db.flush()
        result = dashboard_progress(db, user, answers, now)
        assert result["week_start"] == "2026-10-25T00:00:00+01:00"
        assert result["week_end"] == "2026-11-01T00:00:00+00:00"
        assert result["completed_minutes"] == 120
        assert result["progress_percent"] == 100
        assert result["next_session"]["id"] == str(next_training.id)
        assert result["next_session"]["goal"] == "mobility"
