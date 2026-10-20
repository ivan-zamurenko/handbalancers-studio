"""Real isolated Supabase, mail catcher, JWT and product DB; no provider mocks."""

import asyncio
import json
import re
import secrets
import time
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from studio.auth.gateway import AuthGateway
from studio.auth.jwt import JWTValidator
from studio.auth.oauth import OAuthService
from studio.auth.supabase_adapter import SupabaseAuthAdapter
from studio.auth.token_store import TokenCipher, TokenStore
from studio.main import create_app

from server.tests.support.actors import role_session
from server.tests.support.database_guard import require_test_database
from tools import local_stack

ORIGIN = "http://127.0.0.1:8765"


def test_verify_route_validates_six_digit_code():
    client = TestClient(create_app({"app_env": "test", "public_origin": ORIGIN}))
    response = client.post(
        "/api/auth/verify-email",
        headers={"Origin": ORIGIN},
        json={"email": "member@example.test", "token": "sensitive-invalid-code"},
    )
    assert response.status_code == 422
    assert "sensitive-invalid-code" not in response.text


@pytest.fixture(scope="module")
def live():
    require_test_database()
    workdir = Path(".local-tools/supabase/test").resolve()
    local_stack.run_migrations("test")
    status = json.loads(
        local_stack.cli_output(
            ["status", "--output", "json"], workdir, local_stack.docker_environment()
        )
    )
    gateway = AuthGateway(SupabaseAuthAdapter("http://127.0.0.1:55321", status["ANON_KEY"]))
    engine = create_engine(
        URL.create(
            "postgresql+psycopg",
            username="migration_owner",
            password=local_stack.read_migration_password(workdir),
            host="127.0.0.1",
            port=55322,
            database="postgres",
        ),
        hide_parameters=True,
    )
    yield gateway, engine
    engine.dispose()


@pytest.fixture
def member(live):
    gateway, engine = live
    email = f"verify-{uuid4().hex}@example.test"
    payload = asyncio.run(gateway.signup(email, secrets.token_urlsafe(24), "Іван", "Тестовий"))
    auth_id = payload["user"]["id"] if "user" in payload else payload["id"]
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
        yield client, service, engine, email, auth_id


def code_for(email):
    with httpx.Client(base_url="http://127.0.0.1:55324", timeout=5, trust_env=False) as mail:
        for _ in range(40):
            messages = mail.get("/api/v1/messages").json()["messages"]
            for message in messages:
                if any(recipient["Address"] == email for recipient in message["To"]):
                    body = mail.get("/api/v1/message/" + message["ID"]).json()
                    match = re.search(r"\b[0-9]{6}\b", body["Text"])
                    assert match is not None, "Confirmation email must contain a six-digit code"
                    return match.group(0)
            time.sleep(0.1)
    pytest.fail("Local confirmation email did not arrive within bounded wait")


def profile_count(engine, auth_id):
    with engine.connect() as conn:
        return conn.scalar(
            text("SELECT count(*) FROM studio.users WHERE auth_user_id=:id"), {"id": auth_id}
        )


def test_wrong_code_no_profile(member):
    client, _, engine, email, auth_id = member
    code = code_for(email)
    wrong = "111111" if code != "111111" else "222222"
    response = client.post("/api/auth/verify-email", json={"email": email, "token": wrong})
    assert response.status_code == 422
    assert not response.cookies
    assert profile_count(engine, auth_id) == 0


def test_valid_verified_identity_and_replay(member):
    client, _, engine, email, auth_id = member
    assert profile_count(engine, auth_id) == 0
    code = code_for(email)
    response = client.post("/api/auth/verify-email", json={"email": email, "token": code})
    assert response.status_code == 200
    assert response.json() == {"state": "authenticated", "profile_complete": True}
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie
    snapshot = client.get("/api/session").json()
    assert snapshot["authenticated"] and snapshot["user"]["role"] == "member"
    assert snapshot["user"]["first_name"] == "Іван"
    assert profile_count(engine, auth_id) == 1
    replay = client.post("/api/auth/verify-email", json={"email": email, "token": code})
    assert replay.status_code == 422 and not replay.cookies
    assert profile_count(engine, auth_id) == 1


def test_expired_code_no_profile(member):
    client, _, engine, email, auth_id = member
    code = code_for(email)
    # Only this test-created identity in the guarded local test Auth instance.
    from uuid import UUID

    ident = UUID(auth_id)
    local_stack.execute_local_sql(
        local_stack.verify_container("test"),
        f"UPDATE auth.users SET confirmation_sent_at=now()-interval '2 days' WHERE id='{ident}';",
    )
    response = client.post("/api/auth/verify-email", json={"email": email, "token": code})
    assert response.status_code == 422 and not response.cookies
    assert profile_count(engine, auth_id) == 0


def test_role_always_member_and_retry_provision(member, monkeypatch):
    _, service, engine, email, auth_id = member
    from uuid import UUID

    ident = UUID(auth_id)
    local_stack.execute_local_sql(
        local_stack.verify_container("test"),
        f"UPDATE auth.users SET raw_user_meta_data=raw_user_meta_data || '{{\"role\":\"coach\"}}'::jsonb WHERE id='{ident}';",
    )
    payload = asyncio.run(service.gateway.verify_email(email, code_for(email)))
    # Reprocessing a verified result after a local transaction timeout must not duplicate users.
    with engine.connect() as conn:
        before_sessions = conn.scalar(text("SELECT count(*) FROM studio_private.web_sessions"))
    original = service.store.create_session

    def fail_after_insert(*args, **kwargs):
        original(*args, **kwargs)
        raise TimeoutError("Controlled local transaction interruption")

    with monkeypatch.context() as patch:
        patch.setattr(service.store, "create_session", fail_after_insert)
        with pytest.raises(TimeoutError):
            asyncio.run(service.accept_identity(payload))
    assert profile_count(engine, auth_id) == 0
    with engine.connect() as conn:
        assert (
            conn.scalar(text("SELECT count(*) FROM studio_private.web_sessions")) == before_sessions
        )
    first = asyncio.run(service.accept_identity(payload))
    second = asyncio.run(
        service.accept_identity(payload, old_cookie=first.cookie.get_secret_value())
    )
    assert first.user_id == second.user_id
    with engine.connect() as conn:
        assert (
            conn.scalar(
                text(
                    "SELECT count(*) FROM studio_private.web_sessions WHERE user_id=:id AND revoked_at IS NULL"
                ),
                {"id": first.user_id},
            )
            == 1
        )
    assert profile_count(engine, auth_id) == 1
    with engine.connect() as conn:
        assert (
            conn.scalar(
                text("SELECT role FROM studio.users WHERE auth_user_id=:id"), {"id": auth_id}
            )
            == "member"
        )


def test_resend_limited_neutral_and_origin_guard(member):
    client, _, engine, email, auth_id = member
    unknown = f"unknown-{uuid4().hex}@example.test"
    assert (
        client.post(
            "/api/auth/resend-verification",
            json={"email": email},
            headers={"Origin": "https://untrusted.test"},
        ).status_code
        == 403
    )
    first = client.post("/api/auth/resend-verification", json={"email": email})
    other = client.post("/api/auth/resend-verification", json={"email": unknown})
    assert first.status_code == other.status_code == 202
    assert first.json() == other.json() == {"state": "verification_pending"}
    again = client.post("/api/auth/resend-verification", json={"email": email})
    assert again.status_code == 429 and again.headers["retry-after"] == "60"
    assert profile_count(engine, auth_id) == 0


def test_email_disabled_independently_of_social_service(member):
    client, _, _, email, _ = member
    # Existing OAuth runtime alone must not expose disabled email operations.
    client.app.state.verification_service = None
    for path, payload in [
        ("/verify-email", {"email": email, "token": "123456"}),
        ("/resend-verification", {"email": email}),
    ]:
        response = client.post("/api/auth" + path, json=payload)
        assert response.status_code == 503
        assert not response.cookies


def test_resend_concurrent_quota_and_ip_budget(member):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from studio.auth.oauth import OAuthRateLimited
    from studio.auth.verification import quota

    _, service, _, email, _ = member
    barrier = Barrier(2)

    def attempt(_):
        barrier.wait(timeout=5)
        try:
            quota(service, "resend", email, "concurrent")
            return True
        except OAuthRateLimited:
            return False

    with ThreadPoolExecutor(2) as pool:
        assert sum(pool.map(attempt, range(2))) == 1
    for i in range(10):
        quota(service, "resend", f"{i}-{email}", "rotating-email")
    with pytest.raises(OAuthRateLimited):
        quota(service, "resend", f"last-{email}", "rotating-email")


def test_runtime_email_enabled_without_social_providers():
    import base64

    from pydantic import ValidationError
    from studio.settings import Settings

    with pytest.raises(ValidationError):
        Settings.model_validate({"app_env": "test", "auth_email_enabled": True})
    app = create_app(
        {
            "app_env": "test",
            "public_origin": ORIGIN,
            "auth_email_enabled": True,
            "supabase_url": "http://127.0.0.1:55321",
            "supabase_publishable_key": "test-key",
            "auth_database_url": "postgresql+psycopg://runtime@127.0.0.1:55322/postgres",
            "token_encryption_key": base64.b64encode(b"k" * 32).decode(),
        }
    )
    assert not app.state.oauth_service.providers
    assert app.state.verification_service is app.state.oauth_service
    assert app.state.auth_gateway is app.state.oauth_service.gateway
