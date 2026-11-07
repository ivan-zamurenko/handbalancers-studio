"""Real PostgreSQL revocation; external failures controlled at the gateway boundary."""

import asyncio
import hashlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from studio.auth.gateway import AuthFailure, AuthFailureKind
from studio.auth.token_store import StoreError
from studio.main import create_app

from server.tests.integration.auth import test_oauth_flow as flow_support
from server.tests.integration.auth import test_verify_email as email_support
from server.tests.integration.database.test_auth_storage import (  # noqa: F401
    database_engine,
    storage_db,
)

flow = flow_support.flow
live = email_support.live
member = email_support.member
member_password = email_support.member_password


@pytest.fixture
def signed_in(flow):
    service, calls, engine, _ = flow
    attempt = service.start("google", "/plans")
    result = asyncio.run(
        service.finish("google", attempt.attempt, attempt.binding.get_secret_value(), "code")
    )
    cookie = result.cookie.get_secret_value()
    app = create_app({"app_env": "test", "public_origin": service.public_origin})
    app.state.oauth_service = service
    with TestClient(app, base_url=service.public_origin) as client:
        client.cookies.set("__Host-studio_session", cookie)
        yield client, service, engine, cookie, calls


def post_logout(client, service, cookie):
    return client.post(
        "/api/auth/logout",
        headers={"Origin": service.public_origin, "X-CSRF-Token": service.csrf_token(cookie)},
    )


def test_old_cookie_rejected_before_upstream_completes(signed_in):
    client, service, _, cookie, _ = signed_in

    async def slow_upstream(_token):
        # Another DB transaction must see revocation before network completion.
        with service.transaction() as session, pytest.raises(StoreError):
            service.store.read_session(session, cookie)
        with pytest.raises(StoreError):
            await service.session_profile(cookie)

    service.gateway.logout = slow_upstream
    response = post_logout(client, service, cookie)
    assert response.status_code == 204
    for flag in ["Max-Age=0", "HttpOnly", "Secure", "SameSite=lax", "Path=/"]:
        assert flag in response.headers["set-cookie"]
    client.cookies.set("__Host-studio_session", cookie)
    assert client.get("/api/session").status_code == 401


def test_upstream_outage_local_revoke(signed_in):
    client, service, _, cookie, _ = signed_in

    async def offline(_token):
        raise AuthFailure(AuthFailureKind.UNAVAILABLE)

    service.gateway.logout = offline
    response = post_logout(client, service, cookie)
    assert response.status_code == 204
    assert response.headers["cache-control"] == "no-store"
    client.cookies.set("__Host-studio_session", cookie)
    assert client.get("/api/session").status_code == 401


def test_logout_idempotent_does_not_touch_another_session(signed_in):
    client, service, _, cookie, calls = signed_in
    attempt = service.start("google", "/plans")
    other = asyncio.run(
        service.finish("google", attempt.attempt, attempt.binding.get_secret_value(), "code")
    )
    assert post_logout(client, service, cookie).status_code == 204
    count = len(calls)
    client.cookies.set("__Host-studio_session", cookie)
    assert post_logout(client, service, cookie).status_code == 204
    assert len(calls) == count
    assert asyncio.run(service.session_profile(other.cookie.get_secret_value()))


@pytest.mark.parametrize("state", ["corrupt", "expired"])
def test_unreadable_session_is_still_revoked(signed_in, state):
    client, service, engine, cookie, calls = signed_in
    with engine.begin() as conn:
        statement = (
            "encrypted_tokens='corrupt'"
            if state == "corrupt"
            else "expires_at=clock_timestamp()-interval '1 second'"
        )
        conn.execute(
            text(
                "UPDATE studio_private.web_sessions SET "
                + statement
                + " WHERE session_key_hash=:key"
            ),
            {"key": hashlib.sha256(cookie.encode()).hexdigest()},
        )
    count = len(calls)
    assert post_logout(client, service, cookie).status_code == 204
    assert len(calls) == count
    with engine.connect() as conn:
        assert conn.scalar(
            text(
                "SELECT revoked_at IS NOT NULL FROM studio_private.web_sessions "
                "WHERE session_key_hash=:key"
            ),
            {"key": hashlib.sha256(cookie.encode()).hexdigest()},
        )


def test_upstream_logout_has_total_deadline(signed_in, monkeypatch):
    from studio.auth import logout as module

    client, service, _, cookie, _ = signed_in
    monkeypatch.setattr(module, "UPSTREAM_TIMEOUT_SECONDS", 0.05)

    async def hanging(_token):
        await asyncio.sleep(60)

    service.gateway.logout = hanging
    assert post_logout(client, service, cookie).status_code == 204
    client.cookies.set("__Host-studio_session", cookie)
    assert client.get("/api/session").status_code == 401


def test_real_local_supabase_signout_is_current_session_only(member, member_password):
    client, service, _, email, _ = member
    assert (
        client.post(
            "/api/auth/verify-email", json={"email": email, "token": email_support.code_for(email)}
        ).status_code
        == 200
    )
    cookie = client.cookies.get("studio_local_session")
    with service.transaction() as session:
        old = service.store.read_session(session, cookie)
    other = asyncio.run(service.gateway.password_login(email, member_password))
    assert asyncio.run(service.logout(cookie)) is True
    with pytest.raises(AuthFailure):
        asyncio.run(service.gateway.refresh(old.refresh_token.get_secret_value()))
    assert asyncio.run(service.gateway.refresh(other["refresh_token"]))["access_token"]
    assert post_logout(client, service, cookie).status_code == 204
    assert client.get("/api/session").json() == {"authenticated": False}


def test_old_csrf_cannot_log_out_different_account(signed_in):
    client, service, engine, cookie, _ = signed_in
    other_service, _, _, _ = flow_support.flow.__wrapped__(engine)
    start = other_service.start("google", "/plans")
    other = asyncio.run(
        other_service.finish("google", start.attempt, start.binding.get_secret_value(), "code")
    )
    assert post_logout(client, service, cookie).status_code == 204
    client.app.state.oauth_service = other_service
    client.cookies.clear()
    client.cookies.set("__Host-studio_session", other.cookie.get_secret_value())
    assert post_logout(client, service, cookie).status_code == 403
    assert asyncio.run(other_service.session_profile(other.cookie.get_secret_value()))
