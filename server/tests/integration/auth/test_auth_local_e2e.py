"""S03-11 gate: register -> mail catcher -> verify -> login -> logout on real local Supabase.

No gateway, JWT or mail mocks. Hosted OAuth and external SMTP are not covered here.
"""

import asyncio
import secrets
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from studio.auth.gateway import AuthFailure
from studio.auth.jwt import JWTValidator
from studio.auth.oauth import OAuthService
from studio.auth.token_store import StoreError, TokenCipher, TokenStore
from studio.main import create_app

from server.tests.integration.auth import test_verify_email as email_support
from server.tests.support.actors import role_session
from tools import local_auth_fixture as fixture

ORIGIN = email_support.ORIGIN
COOKIE = "studio_local_session"
live = email_support.live


@pytest.fixture
def studio(live):
    gateway, engine = live
    service = OAuthService(
        auth_transaction=lambda: role_session(engine, "studio_auth_runtime"),
        store=TokenStore(
            TokenCipher("test", {"test": secrets.token_bytes(32)}),
            allowed_return_paths=frozenset({"/plans"}),
        ),
        gateway=gateway,
        validator=JWTValidator(issuer="http://127.0.0.1:55321/auth/v1"),
        supabase_url="http://127.0.0.1:55321",
        public_origin=ORIGIN,
        providers=frozenset(),
    )
    app = create_app({"app_env": "test", "public_origin": ORIGIN})
    app.state.oauth_service = service
    app.state.auth_gateway = gateway
    app.state.verification_service = service
    with TestClient(app, base_url=ORIGIN, headers={"Origin": ORIGIN}) as client:
        yield client, service, engine


@pytest.fixture
def account(studio):
    client, service, engine = studio
    email = fixture.disposable_email("e2e")
    password = secrets.token_urlsafe(24)
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Марта",
            "last_name": "Локальна",
        },
    )
    assert response.status_code == 202, response.text
    assert response.json() == {"state": "verification_pending"}
    return client, service, engine, email, password


def verify(client, email):
    code = fixture.read_code(email)
    response = client.post("/api/auth/verify-email", json={"email": email, "token": code})
    assert response.status_code == 200
    return code, response


def auth_subject(service, cookie):
    with service.transaction() as session:
        secrets_ = service.store.read_session(session, cookie)
    identity = asyncio.run(service.validator.verify(secrets_.access_token.get_secret_value()))
    return identity.user_id, secrets_


def profiles(engine, auth_id):
    with engine.connect() as conn:
        return (
            conn.execute(
                text("SELECT id FROM studio.users WHERE auth_user_id=:id ORDER BY id"),
                {"id": auth_id},
            )
            .scalars()
            .all()
        )


def logout(client):
    csrf = client.get("/api/session").json()["csrf_token"]
    return client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})


def test_actual_email_code(account, caplog):
    client, _, _, email, _ = account
    assert fixture.MAIL_CATCHER_HOST == "127.0.0.1"
    with pytest.raises(fixture.UnsafeMailCatcher):
        fixture.read_code(email, base_url="http://mail.example.test:8025")
    code, response = verify(client, email)
    assert len(code) == 6 and code.isdigit()
    # Message is consumed inside the catcher; no copy remains or leaves the process.
    assert fixture.messages_for(email) == []
    assert code not in response.text + caplog.text
    assert response.json() == {"state": "authenticated", "profile_complete": True}
    assert client.get("/api/session").json()["authenticated"] is True


def test_actual_profile_fk(account):
    client, service, engine, email, _ = account
    verify(client, email)
    auth_id, _ = auth_subject(service, client.cookies.get(COOKIE))
    managed = fixture.managed_user(auth_id)
    assert managed is not None, "Profile owner must exist in real managed auth.users"
    assert managed["email"] == email and managed["confirmed"] is True
    assert len(profiles(engine, auth_id)) == 1
    with engine.connect() as conn:
        constraint = conn.execute(
            text(
                "SELECT confrelid::regclass::text, convalidated FROM pg_constraint "
                "WHERE conname='fk_users_auth_user_id' "
                "AND conrelid='studio.users'::regclass"
            )
        ).one()
    assert tuple(constraint) == ("auth.users", True)


def test_repeat_login_same_profile(account):
    client, service, engine, email, password = account
    verify(client, email)
    auth_id, _ = auth_subject(service, client.cookies.get(COOKIE))
    first = client.get("/api/session").json()["user"]["id"]
    assert logout(client).status_code == 204
    client.cookies.clear()
    login = client.post("/api/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    assert login.json() == {"state": "authenticated", "profile_complete": True}
    second = client.get("/api/session").json()["user"]["id"]
    assert second == first
    assert [str(row) for row in profiles(engine, auth_id)] == [first]


def test_logout_then_refresh_denied(account):
    client, service, _, email, _ = account
    verify(client, email)
    cookie = client.cookies.get(COOKIE)
    _, stored = auth_subject(service, cookie)
    assert logout(client).status_code == 204
    client.cookies.set(COOKIE, cookie, path="/")
    assert client.get("/api/session").status_code == 401
    with service.transaction() as session, pytest.raises(StoreError):
        service.store.read_session(session, cookie)
    with pytest.raises(AuthFailure):
        asyncio.run(service.gateway.refresh(stored.refresh_token.get_secret_value()))
    assert isinstance(stored.upstream_session_id, UUID)
