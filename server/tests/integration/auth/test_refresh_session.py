"""Session refresh must serialize provider rotation and persist token pairs atomically."""

import asyncio
import copy
import hashlib
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from studio.auth.gateway import AuthFailure, AuthFailureKind
from studio.auth.jwt import InvalidIdentity, VerifiedIdentity
from studio.auth.token_store import StoreError
from studio.main import create_app

from server.tests.integration.auth import test_oauth_flow as flow_support
from server.tests.integration.auth import test_verify_email as email_support
from server.tests.integration.database.test_auth_storage import (  # noqa: F401
    database_engine,
    storage_db,
)
from server.tests.support.actors import role_session

flow = flow_support.flow

ROTATED_ACCESS = "synthetic-rotated-access"
ROTATED_REFRESH = "synthetic-rotated-refresh"


@pytest.fixture
def expired_session(flow, monkeypatch):
    service, _, engine, auth_id = flow
    attempt = service.start("google", "/plans")
    result = asyncio.run(
        service.finish("google", attempt.attempt, attempt.binding.get_secret_value(), "code")
    )
    with role_session(engine, "studio_auth_runtime") as session:
        original = service.store.read_session(session, result.cookie.get_secret_value())
        access_expires_at = datetime.now(UTC) + timedelta(seconds=1)
        session_handle = service.store.create_session(
            session,
            user_id=original.user_id,
            upstream_session_id=original.upstream_session_id,
            access_token=original.access_token.get_secret_value(),
            refresh_token="synthetic-expiring-refresh",
            access_expires_at=access_expires_at,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )

    time.sleep(max(0, (access_expires_at - datetime.now(UTC)).total_seconds()) + 0.05)
    original_verify = service.validator.verify
    new_expiry = int(time.time()) + 3600

    async def verify(token):
        if token == original.access_token.get_secret_value():
            if datetime.now(UTC) >= access_expires_at:
                raise InvalidIdentity()
        elif token == ROTATED_ACCESS:
            return VerifiedIdentity(auth_id, original.upstream_session_id, new_expiry)
        return await original_verify(token)

    monkeypatch.setattr(service.validator, "verify", verify)
    app = create_app({"app_env": "test", "public_origin": service.public_origin})
    app.state.oauth_service = service
    cookie_name = (
        "__Host-studio_session"
        if service.public_origin.startswith("https://")
        else ("studio_local_session")
    )
    return service, engine, session_handle.cookie.get_secret_value(), cookie_name, new_expiry


def client_for(service, cookie_name, cookie):
    client = TestClient(
        create_app({"app_env": "test", "public_origin": service.public_origin}),
        base_url=service.public_origin,
    )
    client.app.state.oauth_service = service
    client.cookies.set(cookie_name, cookie, path="/")
    return client


def refresh_response():
    return {
        "access_token": ROTATED_ACCESS,
        "refresh_token": ROTATED_REFRESH,
        "token_type": "bearer",
    }


def test_parallel_refresh_single_exchange(expired_session):
    service, _, cookie, cookie_name, _ = expired_session
    calls = []

    async def refresh(token):
        calls.append(token)
        await asyncio.sleep(0.1)
        return refresh_response()

    service.gateway.refresh = refresh

    def request_session():
        # Distinct service instances must coordinate through PostgreSQL.
        with client_for(copy.copy(service), cookie_name, cookie) as client:
            return client.get("/api/session")

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: request_session(), range(2)))

    assert [response.status_code for response in responses] == [200, 200]
    assert all(response.json()["authenticated"] for response in responses)
    assert calls == ["synthetic-expiring-refresh"]


def test_rotated_tokens_atomic(expired_session):
    service, engine, cookie, cookie_name, new_expiry = expired_session

    async def refresh(token):
        assert token == "synthetic-expiring-refresh"
        return refresh_response()

    service.gateway.refresh = refresh
    with client_for(service, cookie_name, cookie) as client:
        response = client.get("/api/session")
    assert response.status_code == 200 and response.json()["authenticated"]
    with role_session(engine, "studio_auth_runtime") as session:
        stored = service.store.read_session(session, cookie)
    assert stored.access_token.get_secret_value() == ROTATED_ACCESS
    assert stored.refresh_token.get_secret_value() == ROTATED_REFRESH
    assert int(stored.access_expires_at.timestamp()) == new_expiry


def test_revoked_upstream_rejected(expired_session):
    service, engine, cookie, cookie_name, _ = expired_session

    async def revoked(_token):
        raise AuthFailure(AuthFailureKind.INVALID_CREDENTIALS)

    service.gateway.refresh = revoked
    with client_for(service, cookie_name, cookie) as client:
        response = client.get("/api/session")
    assert response.status_code == 401
    with role_session(engine, "studio_auth_runtime") as session, pytest.raises(StoreError):
        service.store.read_session(session, cookie)


def test_transient_error_not_logout_forever(expired_session):
    service, engine, cookie, cookie_name, _ = expired_session

    async def offline(_token):
        raise AuthFailure(AuthFailureKind.TIMEOUT)

    service.gateway.refresh = offline
    with client_for(service, cookie_name, cookie) as client:
        failed = client.get("/api/session")
        assert failed.status_code == 503
        assert failed.headers["cache-control"] == "no-store"

        async def recovered(_token):
            return refresh_response()

        service.gateway.refresh = recovered
        retried = client.get("/api/session")
    assert retried.status_code == 200 and retried.json()["authenticated"]
    with role_session(engine, "studio_auth_runtime") as session:
        assert service.store.read_session(session, cookie).refresh_token.get_secret_value() == (
            ROTATED_REFRESH
        )


@pytest.mark.parametrize(
    "kind", [AuthFailureKind.REJECTED, AuthFailureKind.RATE_LIMIT, AuthFailureKind.UNAVAILABLE]
)
def test_provider_error_classification(expired_session, kind):
    service, engine, cookie, cookie_name, _ = expired_session

    async def failure(_token):
        raise AuthFailure(kind)

    service.gateway.refresh = failure
    with client_for(service, cookie_name, cookie) as client:
        response = client.get("/api/session")
    assert response.status_code == (401 if kind == AuthFailureKind.REJECTED else 503)
    with role_session(engine, "studio_auth_runtime") as session:
        if kind == AuthFailureKind.REJECTED:
            with pytest.raises(StoreError):
                service.store.read_session(session, cookie)
        else:
            assert service.store.read_session(session, cookie)


def test_login_local_lifetime_is_separate(flow):
    service, _, engine, _ = flow
    start = service.start("google", "/plans")
    result = asyncio.run(
        service.finish("google", start.attempt, start.binding.get_secret_value(), "code")
    )
    with engine.connect() as conn:
        access, local = conn.execute(
            text(
                "SELECT access_expires_at, expires_at FROM studio_private.web_sessions "
                "WHERE session_key_hash=:key"
            ),
            {"key": hashlib.sha256(result.cookie.get_secret_value().encode()).hexdigest()},
        ).one()
    assert local > access
    assert timedelta(days=6) < local - datetime.now(UTC) <= timedelta(days=7)


def test_logout_during_exchange_cannot_resurrect(expired_session):
    service, engine, cookie, cookie_name, _ = expired_session

    async def refresh(_token):
        # This transaction must succeed while provider I/O is in progress.
        with role_session(engine, "studio_auth_runtime") as session:
            session.execute(text("SET LOCAL lock_timeout='200ms'"))
            service.store.revoke_session(session, cookie)
        return refresh_response()

    service.gateway.refresh = refresh
    with client_for(service, cookie_name, cookie) as client:
        response = client.get("/api/session")
    assert response.status_code == 401
    with role_session(engine, "studio_auth_runtime") as session, pytest.raises(StoreError):
        service.store.read_session(session, cookie)


@pytest.mark.parametrize("claim", ["user", "session"])
def test_refresh_identity_cannot_change(expired_session, monkeypatch, claim):
    from uuid import uuid4

    service, engine, cookie, cookie_name, expiry = expired_session
    with role_session(engine, "studio_auth_runtime") as session:
        tokens = service.store.read_session(session, cookie)
    original_verify = service.validator.verify
    original_identity = asyncio.run(original_verify(ROTATED_ACCESS))

    async def verify(token):
        if token == ROTATED_ACCESS:
            return VerifiedIdentity(
                uuid4() if claim == "user" else original_identity.user_id,
                uuid4() if claim == "session" else tokens.upstream_session_id,
                expiry,
            )
        return await original_verify(token)

    async def refresh(_token):
        return refresh_response()

    monkeypatch.setattr(service.validator, "verify", verify)
    service.gateway.refresh = refresh
    with client_for(service, cookie_name, cookie) as client:
        response = client.get("/api/session")
    assert response.status_code == 401
    with role_session(engine, "studio_auth_runtime") as session, pytest.raises(StoreError):
        service.store.read_session(session, cookie)


def test_refresh_grants_are_column_limited(expired_session):
    _, engine, _, _, _ = expired_session
    allowed = {"encrypted_tokens", "access_expires_at", "last_seen_at", "row_version", "revoked_at"}
    with engine.connect() as conn:
        columns = conn.execute(
            text(
                "SELECT column_name, has_column_privilege('studio_auth_runtime', "
                "'studio_private.web_sessions',column_name,'UPDATE') "
                "FROM information_schema.columns WHERE table_schema='studio_private' "
                "AND table_name='web_sessions'"
            )
        ).all()
    assert {name for name, granted in columns if granted} == allowed
    with role_session(engine, "studio_auth_runtime") as session, pytest.raises(ProgrammingError):
        session.execute(text("UPDATE studio_private.web_sessions SET expires_at=now()"))


def test_busy_lease_is_bounded_and_recovers(expired_session, monkeypatch):
    from studio.auth import refresh as module

    service, engine, cookie, cookie_name, _ = expired_session
    with service.transaction() as session:
        lease = service.store.claim_refresh(session, cookie)
    assert lease is not None
    monkeypatch.setattr(module, "WAIT_SECONDS", 0.1)
    with client_for(service, cookie_name, cookie) as client:
        started = time.monotonic()
        response = client.get("/api/session")
    assert response.status_code == 503
    assert time.monotonic() - started < 1
    # Simulate a crashed worker: recovery uses DB time, never browser time.
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE studio_private.web_sessions SET last_seen_at="
                "clock_timestamp()-interval '31 seconds' WHERE session_key_hash=:key"
            ),
            {"key": hashlib.sha256(cookie.encode()).hexdigest()},
        )
    with service.transaction() as session:
        replacement = service.store.claim_refresh(session, cookie)
    assert replacement > lease
    with service.transaction() as session:
        assert not service.store.release_refresh(session, cookie, lease, revoke=True)
        assert not service.store.complete_refresh(
            session,
            cookie,
            lease,
            access_token="stale",
            refresh_token="stale",
            access_expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        assert service.store.release_refresh(session, cookie, replacement)

    async def refresh(_token):
        return refresh_response()

    service.gateway.refresh = refresh
    with client_for(service, cookie_name, cookie) as client:
        assert client.get("/api/session").status_code == 200


def test_token_swap_rolls_back_as_one_unit(expired_session):
    service, _, cookie, _, _ = expired_session
    with service.transaction() as session:
        before = service.store.read_session(session, cookie)
        lease = service.store.claim_refresh(session, cookie)
    with pytest.raises(RuntimeError, match="rollback"), service.transaction() as session:
        assert service.store.complete_refresh(
            session,
            cookie,
            lease,
            access_token=ROTATED_ACCESS,
            refresh_token=ROTATED_REFRESH,
            access_expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        raise RuntimeError("rollback")
    with service.transaction() as session:
        assert service.store.read_session(session, cookie) == before
        assert service.store.release_refresh(session, cookie, lease)


@pytest.mark.parametrize("mode", ["timeout", "cancel"])
def test_interrupted_refresh_releases_lease(expired_session, monkeypatch, mode):
    from studio.auth import refresh as module

    service, _, cookie, _, _ = expired_session
    started = asyncio.Event()

    async def slow(_token):
        started.set()
        await asyncio.sleep(60)

    service.gateway.refresh = slow
    monkeypatch.setattr(module, "EXCHANGE_SECONDS", 0.05)

    async def run():
        task = asyncio.create_task(service.session_profile(cookie))
        await started.wait()
        if mode == "cancel":
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            with pytest.raises(module.RefreshUnavailable):
                await task

    asyncio.run(run())
    with service.transaction() as session:
        lease = service.store.claim_refresh(session, cookie)
        assert lease is not None
        service.store.release_refresh(session, cookie, lease)


def test_unavailable_jwt_validation_keeps_retryable_session(expired_session, monkeypatch):
    service, _, cookie, cookie_name, _ = expired_session

    async def refresh(_token):
        return refresh_response()

    async def missing_keys(_token):
        # JWTValidator also raises InvalidIdentity when JWKS is unavailable.
        raise InvalidIdentity()

    service.gateway.refresh = refresh
    monkeypatch.setattr(service.validator, "verify", missing_keys)
    with client_for(service, cookie_name, cookie) as client:
        assert client.get("/api/session").status_code == 503
    with service.transaction() as session:
        assert service.store.read_session(session, cookie)


live = email_support.live
member = email_support.member
member_password = email_support.member_password


def test_real_local_supabase_refresh(member, caplog):
    client, service, _, email, _ = member
    confirmed = client.post(
        "/api/auth/verify-email", json={"email": email, "token": email_support.code_for(email)}
    )
    assert confirmed.status_code == 200
    original_cookie = client.cookies.get("studio_local_session")
    early_expiry = datetime.now(UTC) + timedelta(seconds=1)
    with service.transaction() as session:
        original = service.store.read_session(session, original_cookie)
        handle = service.store.create_session(
            session,
            user_id=original.user_id,
            upstream_session_id=original.upstream_session_id,
            access_token=original.access_token.get_secret_value(),
            refresh_token=original.refresh_token.get_secret_value(),
            access_expires_at=early_expiry,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
    # Force local cache expiry; the provider and JWT verification remain real.
    time.sleep(max(0, (early_expiry - datetime.now(UTC)).total_seconds()) + 0.05)
    client.cookies.clear()
    client.cookies.set("studio_local_session", handle.cookie.get_secret_value(), path="/")
    response = client.get("/api/session")
    assert response.status_code == 200
    assert response.json()["authenticated"]
    with service.transaction() as session:
        rotated = service.store.read_session(session, handle.cookie.get_secret_value())
    assert bool(rotated.refresh_token != original.refresh_token)
    assert rotated.access_expires_at > early_expiry
    identity = asyncio.run(service.validator.verify(rotated.access_token.get_secret_value()))
    assert identity.session_id == original.upstream_session_id
    for token in (rotated.access_token, rotated.refresh_token):
        assert token.get_secret_value() not in response.text + caplog.text


@pytest.mark.parametrize(
    "payload", [None, {}, {"access_token": ROTATED_ACCESS, "refresh_token": "x" * 70000}]
)
def test_malformed_refresh_response_is_retryable(expired_session, payload):
    service, _, cookie, cookie_name, _ = expired_session

    async def malformed(_token):
        return payload

    service.gateway.refresh = malformed
    with client_for(service, cookie_name, cookie) as client:
        response = client.get("/api/session")
    assert response.status_code == 503
    with service.transaction() as session:
        assert service.store.read_session(session, cookie)
