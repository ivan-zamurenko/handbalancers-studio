"""Guest validation is credential-free; persisted account writes use the existing guard."""

import pytest
from fastapi.testclient import TestClient
from studio.main import create_app

ORIGIN = "http://testserver"
VALID = {
    "goal_codes": ["handstand"],
    "self_reported_level": 2,
    "session_minutes": 90,
    "weekdays": [1, 3, 5],
    "time_of_day": None,
}


@pytest.fixture
def client():
    return TestClient(create_app({"app_env": "test", "public_origin": ORIGIN}))


def test_guest_validation_no_identity_or_database(client):
    response = client.post("/api/onboarding/draft", json=VALID, headers={"Origin": ORIGIN})
    assert response.status_code == 200
    assert response.json() == VALID
    assert response.headers["cache-control"] == "no-store"
    assert "set-cookie" not in response.headers


@pytest.mark.parametrize(
    "headers", [{}, {"Origin": "https://other.test"}, [("Origin", ORIGIN), ("Origin", ORIGIN)]]
)
def test_pre_auth_csrf_rejects_missing_foreign_duplicate_origin(client, headers):
    response = client.post("/api/onboarding/draft", json=VALID, headers=headers)
    assert response.status_code == 403


@pytest.mark.parametrize(
    "changes",
    [
        {"weekdays": []},
        {"weekdays": [1, 1]},
        {"weekdays": [1, 2, 3, 4]},
        {"goal_codes": ["invented"]},
        {"goal_codes": ["handstand", "handstand"]},
        {"self_reported_level": 4},
        {"session_minutes": 75},
        {"session_minutes": True},
        {"birth_year": 1990},
        {"weight_kg": 75},
        {"user_id": "someone"},
        {"role": "coach"},
        {"expected_revision": 9},
        {"tier": "pro"},
    ],
)
def test_strict_non_sensitive_allowlist(client, changes):
    response = client.post(
        "/api/onboarding/draft", json={**VALID, **changes}, headers={"Origin": ORIGIN}
    )
    assert response.status_code == 422


def test_public_questionnaire_is_available_without_auth(client):
    response = client.get("/onboarding?lang=en")
    assert response.status_code == 200
    assert "data-guest-form" in response.text
    assert 'name="birth_year"' not in response.text
    assert 'name="weekdays"' in response.text
