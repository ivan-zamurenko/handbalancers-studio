"""S05-01: questionnaire = self-report, validated identically by API and DB; own row only."""

from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from server.tests.integration.database.test_auth_storage import (  # noqa: F401
    database_engine,
    storage_db,
)
from server.tests.security.accounts import test_profile_preferences as profile_support
from server.tests.support.actors import role_session

flow = profile_support.flow
device = profile_support.device

VALID = {
    "goal_codes": ["handstand", "strength"],
    "self_reported_level": 2,
    "session_minutes": 90,
    "weekdays": [1, 3, 5],
    "time_of_day": "evening",
    "expected_revision": 0,
}


def put(client, **changes):
    return client.put("/api/me/onboarding", json={**VALID, **changes})


def test_ninety_minutes_accepted(device):
    open_device, db, auth_id = device
    client = open_device()
    saved = put(client)
    assert saved.status_code == 200, saved.text
    assert saved.json()["session_minutes"] == 90
    assert client.get("/api/me/onboarding").json()["session_minutes"] == 90
    with db.connect() as conn:
        stored = conn.scalar(
            text(
                "SELECT o.session_minutes FROM studio.onboarding_profiles o "
                "JOIN studio.users u ON u.id = o.user_id WHERE u.auth_user_id = :a"
            ),
            {"a": auth_id},
        )
    assert stored == 90
    assert put(client, session_minutes=75, expected_revision=1).status_code == 422


@pytest.mark.parametrize("weekdays", [[1, 1], [1, 2, 3, 4], [0], [8], [], ["mon"]], ids=str)
def test_unique_weekdays(device, weekdays):
    open_device, db, _ = device
    client = open_device()
    assert put(client, weekdays=weekdays).status_code == 422
    assert client.get("/api/me/onboarding").json() is None
    # The database enforces the same rule when the API is bypassed.
    if weekdays and all(isinstance(d, int) for d in weekdays):
        user = UUID(client.get("/api/session").json()["user"]["id"])
        with pytest.raises(IntegrityError), role_session(db, "studio_web", user) as session:
            session.execute(
                text(
                    "INSERT INTO studio.onboarding_profiles "
                    "(user_id, goal_codes, self_reported_level, session_minutes, weekdays) "
                    "VALUES (:u, ARRAY['fitness'], 1, 30, :d)"
                ),
                {"u": user, "d": weekdays},
            )


def test_multiple_equal_goals(device):
    open_device, _, _ = device
    client = open_device()
    four = ["handstand", "strength", "mobility", "fitness"]
    saved = put(client, goal_codes=four)
    assert saved.status_code == 200 and saved.json()["goal_codes"] == four
    assert "primary_goal" not in saved.json()
    for bad in ([], ["handstand", "handstand"], ["yoga"]):
        assert put(client, goal_codes=bad, expected_revision=1).status_code == 422


def test_self_report_not_assessment(device):
    open_device, db, _ = device
    client = open_device()
    saved = put(client, self_reported_level=3).json()
    assert saved["self_reported_level"] == 3
    assert not {"readiness", "assessment", "score"} & set(saved)
    with db.connect() as conn:
        assessment_tables = conn.scalar(
            text(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema LIKE 'studio%' AND table_name ILIKE '%assess%'"
            )
        )
    assert assessment_tables == 0
    assert put(client, self_reported_level=4, expected_revision=1).status_code == 422


def test_revision_body_metrics_and_isolation(device):
    open_device, db, _ = device
    phone, laptop = open_device(), open_device()
    first = put(phone, birth_year=1992, height_cm=178, weight_kg=74.5)
    assert first.status_code == 200 and first.json()["revision"] == 1
    assert (first.json()["birth_year"], first.json()["weight_kg"]) == (1992, 74.5)
    stale = put(laptop, session_minutes=30)
    assert stale.status_code == 409 and stale.json()["current"]["session_minutes"] == 90
    assert put(laptop, height_cm=20, expected_revision=1).status_code == 422
    cleared = put(laptop, expected_revision=1)
    assert cleared.status_code == 200 and cleared.json()["birth_year"] is None
    stranger = UUID("00000000-0000-4000-8000-000000000099")
    with role_session(db, "studio_web", stranger) as session:
        assert session.scalar(text("SELECT count(*) FROM studio.onboarding_profiles")) == 0


def test_session_reports_setup_required(device):
    open_device, _, _ = device
    client = open_device()
    assert client.get("/api/session").json()["setup_required"] is True
    put(client)
    client.patch("/api/me/profile", json={"first_name": "Іван", "last_name": "Петренко"})
    assert client.get("/api/session").json()["setup_required"] is False
