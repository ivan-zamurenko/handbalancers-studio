"""Real local Auth password exchange, product DB, JWT and opaque session rotation."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from studio.auth.token_store import StoreError

from server.tests.integration.auth import test_verify_email as email_support
from server.tests.support.actors import role_session

live = email_support.live
member = email_support.member
member_password = email_support.member_password
code_for = email_support.code_for
profile_count = email_support.profile_count

def confirm(member):
    client, _, _, email, _ = member
    result = client.post("/api/auth/verify-email", json={"email": email, "token": code_for(email)})
    assert result.status_code == 200


def test_valid_login_rotates_cookie(member, member_password, caplog):
    client, service, engine, email, auth_id = member
    confirm(member)
    old = client.cookies.get("studio_local_session")
    response = client.post("/api/auth/login", json={"email": email, "password": member_password})
    assert response.status_code == 200
    assert response.json() == {"state": "authenticated", "profile_complete": True}
    new = client.cookies.get("studio_local_session")
    assert new and new != old
    with role_session(engine, "studio_auth_runtime") as session, pytest.raises(StoreError):
        service.store.read_session(session, old)
    snapshot = client.get("/api/session")
    assert snapshot.status_code == 200 and snapshot.json()["authenticated"]
    assert snapshot.json()["user"]["role"] == "member"
    assert snapshot.json()["entitlements"] == []
    assert "access_token" not in snapshot.text and "refresh_token" not in snapshot.text
    assert member_password not in caplog.text + response.text
    assert profile_count(engine, auth_id) == 1
    client.cookies.clear()
    client.cookies.set(
        "studio_local_session", "attacker-preauth-cookie", domain="127.0.0.1", path="/"
    )
    response = client.post("/api/auth/login", json={"email": email, "password": member_password})
    assert response.status_code == 200
    assert client.cookies.get("studio_local_session") != "attacker-preauth-cookie"


def test_invalid_login_generic_and_unverified(member, member_password):
    client, _, engine, email, auth_id = member
    results = []
    for address, password in [
        (email, "wrong-password"),
        (f"absent-{uuid4().hex}@example.test", "wrong-password"),
        (email, member_password),
    ]:
        response = client.post("/api/auth/login", json={"email": address, "password": password})
        assert response.status_code == 401 and not response.cookies
        assert response.headers["cache-control"] == "no-store"
        body = response.json()
        body["error"].pop("request_id", None)
        results.append(body)
    assert results[0] == results[1] == results[2]
    assert profile_count(engine, auth_id) == 0
    assert client.get("/api/session").json() == {"authenticated": False}


def test_secure_cookie_and_current_inactive_profile(member, member_password):
    client, _, engine, email, auth_id = member
    confirm(member)
    origin = "https://studio.example.test"
    from studio.settings import Settings

    app = client.app
    app.state.settings = Settings(app_env="test", public_origin=origin)
    with TestClient(app, base_url=origin, headers={"origin": origin}) as https:
        response = https.post("/api/auth/login", json={"email": email, "password": member_password})
        assert response.status_code == 200
        cookie = response.headers["set-cookie"]
        for flag in ["__Host-studio_session=", "HttpOnly", "Secure", "SameSite=lax", "Path=/"]:
            assert flag in cookie
        assert "Domain=" not in cookie
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE studio.users SET is_active=false WHERE auth_user_id=:id"),
                {"id": auth_id},
            )
        assert https.get("/api/session").status_code == 401
        denied = https.post("/api/auth/login", json={"email": email, "password": member_password})
        assert denied.status_code == 401 and not denied.cookies


def test_login_limited_and_upstream_outage(member, member_password, monkeypatch):
    client, service, _, email, _ = member
    from studio.auth.gateway import AuthFailure, AuthFailureKind

    calls = []

    async def offline(*args):
        calls.append(True)
        raise AuthFailure(AuthFailureKind.TIMEOUT)

    monkeypatch.setattr(service.gateway, "password_login", offline)
    for _ in range(10):
        response = client.post(
            "/api/auth/login", json={"email": email, "password": member_password}
        )
        assert response.status_code == 503 and not response.cookies
        assert response.headers["cache-control"] == "no-store"
    response = client.post("/api/auth/login", json={"email": email, "password": member_password})
    assert response.status_code == 429 and response.headers["retry-after"] == "60"
    assert len(calls) == 10
