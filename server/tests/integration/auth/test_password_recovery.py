"""Recovery uses real local Supabase OTP/password exchange and least-privilege DB."""

import asyncio
import hashlib
import hmac
import re
import secrets
import time
import tomllib
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import text
from studio.auth.gateway import AuthFailure
from studio.auth.jwt import InvalidIdentity
from studio.auth.oauth import OAuthRateLimited

from server.tests.integration.auth import test_password_login as login_support
from server.tests.integration.auth import test_verify_email as email_support
from tools import local_stack

live = email_support.live
member = email_support.member
member_password = email_support.member_password
# Single source of truth for the configured recovery subject (owner chose English emails).
RECOVERY_SUBJECT = tomllib.loads(Path("supabase/config.toml").read_text())["auth"]["email"][
    "template"
]["recovery"]["subject"]


def request_code(client, email):
    result = client.post("/api/auth/recovery/request", json={"email": email})
    assert result.status_code == 202
    with httpx.Client(base_url="http://127.0.0.1:55324", timeout=5, trust_env=False) as mail:
        for _ in range(40):
            for message in mail.get("/api/v1/messages").json()["messages"]:
                if message["Subject"] == RECOVERY_SUBJECT and any(
                    r["Address"] == email for r in message["To"]
                ):
                    body = mail.get("/api/v1/message/" + message["ID"]).json()
                    match = re.search(r"\b[0-9]{6}\b", body["Text"])
                    assert match is not None, "Recovery template must contain six-digit OTP"
                    return match.group(0)
            time.sleep(0.1)
    pytest.fail("Local recovery email did not arrive within bounded wait")


def test_generic_recovery_email(member):
    client, _, _, email, _ = member
    login_support.confirm(member)
    for address in (email, f"absent-{uuid4().hex}@example.test"):
        result = client.post("/api/auth/recovery/request", json={"email": address})
        assert result.status_code == 202
        assert result.json() == {"state": "recovery_pending"}
        assert not result.cookies


def test_post_reset_login_and_recovery_scope_only(member, member_password, caplog):
    client, service, engine, email, auth_id = member
    login_support.confirm(member)
    first = client.cookies.get("studio_local_session")
    # A second device has its own session; both must be retired by recovery.
    client.cookies.clear()
    assert (
        client.post(
            "/api/auth/login", json={"email": email, "password": member_password}
        ).status_code
        == 200
    )
    second = client.cookies.get("studio_local_session")
    code = request_code(client, email)
    client.cookies.clear()
    assert client.get("/api/session").json() == {"authenticated": False}
    new_password = secrets.token_urlsafe(24)
    payload = {"email": email, "token": code, "password": new_password}
    result = client.post("/api/auth/recovery/confirm", json=payload)
    assert result.status_code == 200
    assert result.json() == {"state": "password_changed", "login_required": True}
    assert client.get("/api/session").json() == {"authenticated": False}
    for cookie in (first, second):
        client.cookies.set("studio_local_session", cookie)
        assert client.get("/api/session").status_code == 401
        client.cookies.clear()
    with engine.connect() as connection:
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM studio_private.web_sessions s JOIN studio.users u ON u.id=s.user_id WHERE u.auth_user_id=:id AND s.revoked_at IS NULL"
                ),
                {"id": auth_id},
            )
            == 0
        )
    replay = client.post("/api/auth/recovery/confirm", json=payload)
    assert replay.status_code == 429  # Per-account confirm cooldown precedes provider replay check.
    # Move only this test's account budget beyond its window; upstream OTP must
    # still reject replay, independently of the app's concurrent-confirm guard.
    bucket = hmac.new(
        service.secret, f"recovery-confirm:email:{email.casefold()}".encode(), hashlib.sha256
    ).hexdigest()
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE studio_private.auth_rate_limits SET window_start=now()-interval '2 minutes' WHERE bucket_hash=:bucket"
            ),
            {"bucket": bucket},
        )
    assert client.post("/api/auth/recovery/confirm", json=payload).status_code == 422
    assert (
        client.post(
            "/api/auth/login", json={"email": email, "password": member_password}
        ).status_code
        == 401
    )
    assert (
        client.post("/api/auth/login", json={"email": email, "password": new_password}).status_code
        == 200
    )
    for secret in (code, new_password, member_password):
        assert secret not in result.text + caplog.text


def test_expired_recovery_rejected(member, member_password):
    client, _, _, email, auth_id = member
    login_support.confirm(member)
    code = request_code(client, email)
    ident = UUID(auth_id)
    # Test-created identity on a guarded disposable local Auth instance only.
    local_stack.execute_local_sql(
        local_stack.verify_container("test"),
        f"UPDATE auth.users SET recovery_sent_at=now()-interval '2 days' WHERE id='{ident}';",
    )
    result = client.post(
        "/api/auth/recovery/confirm",
        json={"email": email, "token": code, "password": secrets.token_urlsafe(24)},
    )
    assert result.status_code == 422
    assert (
        client.post(
            "/api/auth/login", json={"email": email, "password": member_password}
        ).status_code
        == 200
    )


def test_recovery_request_quota_does_not_reveal_account(member):
    client, _, _, email, _ = member
    # Local request cooldown is charged even if the provider does not know this email.
    for address in (email, f"absent-{uuid4().hex}@example.test"):
        assert client.post("/api/auth/recovery/request", json={"email": address}).status_code == 202
        assert client.post("/api/auth/recovery/request", json={"email": address}).status_code == 429


def test_delayed_pre_reset_identity_cannot_issue_cookie(member, member_password):
    client, service, engine, email, auth_id = member
    login_support.confirm(member)
    delayed_payload = asyncio.run(service.gateway.password_login(email, member_password))
    code = request_code(client, email)
    response = client.post(
        "/api/auth/recovery/confirm",
        json={
            "email": email,
            "token": code,
            "password": secrets.token_urlsafe(24),
        },
    )
    assert response.status_code == 200
    with pytest.raises((AuthFailure, InvalidIdentity)):
        asyncio.run(service.accept_identity(delayed_payload))
    with engine.connect() as connection:
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM studio_private.web_sessions s JOIN studio.users u ON u.id=s.user_id WHERE u.auth_user_id=:id AND s.revoked_at IS NULL"
                ),
                {"id": auth_id},
            )
            == 0
        )


def test_concurrent_confirmation_consumes_code_once(member, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from studio.auth.recovery import confirm_recovery

    client, service, _, email, _ = member
    login_support.confirm(member)
    code = request_code(client, email)
    barrier = Barrier(2)
    new_password = secrets.token_urlsafe(24)
    events = []
    for name in ("verify_recovery", "update_password", "logout_all", "logout"):
        original = getattr(service.gateway, name)

        async def observed(*args, _name=name, _original=original):
            try:
                result = await _original(*args)
                events.append((_name, "ok"))
                return result
            except AuthFailure as error:
                events.append((_name, error.kind.value))
                raise

        monkeypatch.setattr(service.gateway, name, observed)

    def confirm(_):
        barrier.wait(timeout=5)
        try:
            asyncio.run(confirm_recovery(service, email, code, new_password, client_key="race"))
            return True
        except OAuthRateLimited:
            return False

    with ThreadPoolExecutor(2) as pool:
        assert sum(pool.map(confirm, range(2))) == 1, events
    assert events.count(("verify_recovery", "ok")) == 1
    assert events.count(("update_password", "ok")) == 1
    assert (
        client.post("/api/auth/login", json={"email": email, "password": new_password}).status_code
        == 200
    )
