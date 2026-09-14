"""Membership choices, access boundaries and progress from completed sessions."""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from studio.models import Subscription, TrainingSession, utcnow
from tests.conftest import csrf_headers, register_demo

pytestmark = pytest.mark.postgres


def seed_subscription(client, db_factory, days=20, status="active"):
    owner = uuid.UUID(client.get("/api/session").json()["user"]["id"])
    with db_factory() as db:
        db.add(
            Subscription(
                user_id=owner,
                plan_id="plus",
                is_demo=True,
                status=status,
                current_period_end=utcnow() + timedelta(days=days),
            )
        )
        db.commit()
    return owner


def test_anonymous_plan_survives_registration_rotation(client, answers):
    headers = csrf_headers(client)
    old_cookie = client.cookies.get("studio_session")
    assert (
        client.post("/api/plan", json={"plan_id": "essential"}, headers=headers).status_code == 200
    )
    assert client.get("/api/session").json()["selected_plan"] == "essential"
    register_demo(client, answers)
    assert client.cookies.get("studio_session") != old_cookie
    assert client.get("/api/session").json()["selected_plan"] == "essential"
    assert (
        client.post(
            "/api/plan", json={"plan_id": "invented"}, headers=csrf_headers(client)
        ).status_code
        == 422
    )
    assert client.get("/api/session").json()["selected_plan"] == "essential"


@pytest.mark.parametrize(
    "days,status,indicator,public_status",
    [
        (20, "active", "active", "active"),
        (5, "active", "ending", "active"),
        (3, "trialing", "ending", "trialing"),
        (-1, "active", "inactive", "expired"),
        (20, "canceled", "inactive", "canceled"),
    ],
)
def test_subscription_indicator(
    client, answers, db_factory, days, status, indicator, public_status
):
    register_demo(client, answers)
    seed_subscription(client, db_factory, days, status)
    subscription = client.get("/api/session").json()["subscription"]
    assert subscription["indicator"] == indicator
    assert subscription["status"] == public_status
    assert subscription["days_remaining"] == max(0, days)


def test_inactive_account_can_edit_profile_but_not_log_training(client, answers):
    headers = register_demo(client, answers)
    assert client.get("/api/session").json()["subscription"] is None
    assert (
        client.post(
            "/api/training-sessions", json={"minutes": 30, "goal": "strength"}, headers=headers
        ).status_code
        == 402
    )
    profile = client.patch(
        "/api/profile", json={"first_name": "Іван", "last_name": "Тест"}, headers=headers
    )
    assert profile.status_code == 200
    assert profile.json()["name"] == "Іван Тест"


def test_unauthenticated_training_is_rejected(client):
    assert (
        client.post(
            "/api/training-sessions",
            json={"minutes": 30, "goal": "strength"},
            headers=csrf_headers(client),
        ).status_code
        == 401
    )


def test_completed_training_updates_only_authenticated_owner(client, answers, db_factory):
    headers = register_demo(client, answers)
    owner = seed_subscription(client, db_factory)
    spoofed = {"minutes": 30, "goal": "strength", "user_id": str(uuid.uuid4())}
    assert client.post("/api/training-sessions", json=spoofed, headers=headers).status_code == 422
    assert (
        client.post(
            "/api/training-sessions", json={"minutes": 30, "goal": "mobility"}, headers=headers
        ).status_code
        == 422
    )
    result = client.post(
        "/api/training-sessions", json={"minutes": 30, "goal": "strength"}, headers=headers
    )
    assert result.status_code == 201
    progress = result.json()["progress"]
    assert progress["completed_minutes"] == 30
    assert progress["target_minutes"] == 90
    assert progress["completed_sessions"] == 1
    assert progress["progress_percent"] == 33.3
    with db_factory() as db:
        records = list(db.scalars(select(TrainingSession)))
        assert len(records) == 1
        assert records[0].user_id == owner
    client.cookies.clear()
    register_demo(client, answers)
    other_progress = client.get("/api/session").json()["progress"]
    assert other_progress["completed_minutes"] == 0
    assert other_progress["completed_sessions"] == 0


def test_expired_membership_cannot_write_training(client, answers, db_factory):
    headers = register_demo(client, answers)
    seed_subscription(client, db_factory, days=-1)
    assert (
        client.post(
            "/api/training-sessions", json={"minutes": 30, "goal": "strength"}, headers=headers
        ).status_code
        == 402
    )
