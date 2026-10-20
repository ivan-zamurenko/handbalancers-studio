"""HTTP boundary tests; real password/session/rotation proofs are integration tests."""

import pytest
from fastapi.testclient import TestClient
from studio.main import create_app

ORIGIN = "https://studio.example.test"


def test_login_route_exists_and_hides_invalid_password():
    client = TestClient(create_app({"app_env": "test", "public_origin": ORIGIN}), base_url=ORIGIN)
    response = client.post(
        "/api/auth/login",
        headers={"origin": ORIGIN},
        json={"email": "member@example.test", "password": "x" * 257},
    )
    assert response.status_code == 422
    assert "x" * 257 not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert not response.cookies


@pytest.mark.parametrize("origin", [None, "https://evil.example.test"])
def test_login_origin_denied(origin):
    client = TestClient(create_app({"app_env": "test", "public_origin": ORIGIN}), base_url=ORIGIN)
    response = client.post(
        "/api/auth/login",
        headers={"origin": origin} if origin else {},
        json={"email": "member@example.test", "password": "synthetic-password"},
    )
    assert response.status_code == 403
    assert response.headers["cache-control"] == "no-store"
    assert not response.cookies


def test_disabled_email_login():
    client = TestClient(create_app({"app_env": "test", "public_origin": ORIGIN}), base_url=ORIGIN)
    response = client.post(
        "/api/auth/login",
        headers={"origin": ORIGIN},
        json={"email": "member@example.test", "password": "synthetic-password"},
    )
    assert response.status_code == 503
    assert response.headers["cache-control"] == "no-store"
    assert not response.cookies
