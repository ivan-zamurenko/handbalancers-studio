"""Recovery HTTP guards; real OTP/replay/password proofs live in integration tests."""

import pytest
from fastapi.testclient import TestClient
from studio.main import create_app

ORIGIN = "https://studio.example.test"
REQUEST = {"email": "member@example.test"}
CONFIRM = {**REQUEST, "token": "123456", "password": "new-synthetic-password"}


@pytest.fixture
def client():
    return TestClient(create_app({"app_env": "test", "public_origin": ORIGIN}), base_url=ORIGIN)


@pytest.mark.parametrize("action,payload", [("request", REQUEST), ("confirm", CONFIRM)])
@pytest.mark.parametrize("origin", [None, "https://untrusted.test"])
def test_recovery_origin_denied(client, action, payload, origin):
    response = client.post(
        "/api/auth/recovery/" + action,
        headers={"Origin": origin} if origin else {},
        json=payload,
    )
    assert response.status_code == 403
    assert response.headers["cache-control"] == "no-store"
    assert not response.cookies


@pytest.mark.parametrize("action,payload", [("request", REQUEST), ("confirm", CONFIRM)])
def test_disabled_recovery_fails_closed(client, action, payload):
    response = client.post("/api/auth/recovery/" + action, json=payload, headers={"Origin": ORIGIN})
    assert response.status_code == 503
    assert not response.cookies


@pytest.mark.parametrize(
    "field,value", [("password", "short"), ("password", "s" * 257), ("token", "1234567")]
)
def test_invalid_recovery_input_never_echoes_secrets(client, field, value):
    response = client.post(
        "/api/auth/recovery/confirm", json={**CONFIRM, field: value}, headers={"Origin": ORIGIN}
    )
    assert response.status_code == 422
    assert value not in response.text
    assert CONFIRM["password"] not in response.text
    assert not response.cookies


def test_recovery_page_is_not_authenticated(client):
    response = client.get("/recovery?lang=uk")
    assert response.status_code == 200
    assert 'id="recovery-form"' in response.text
    assert not response.cookies
    assert client.get("/api/session").json() == {"authenticated": False}
