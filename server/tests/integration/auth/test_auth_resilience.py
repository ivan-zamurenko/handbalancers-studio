"""Real DB transactions must not stop unrelated requests on the same ASGI loop."""

import asyncio
import time
from contextlib import contextmanager
from threading import Event

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from studio.auth.jwt import JWTValidator
from studio.main import create_app

from server.tests.integration.auth import test_oauth_flow as flow_support
from server.tests.integration.auth import test_refresh_session as refresh_support
from server.tests.integration.database.test_auth_storage import (  # noqa: F401
    database_engine,
    storage_db,
)

flow = flow_support.flow
expired_session = refresh_support.expired_session


def signed_session(service):
    attempt = service.start("google", "/plans")
    return asyncio.run(
        service.finish(
            "google",
            attempt.attempt,
            attempt.binding.get_secret_value(),
            "synthetic-code",
        )
    ).cookie.get_secret_value()


def app_for(service):
    app = create_app({"app_env": "test", "public_origin": service.public_origin})
    app.state.oauth_service = service
    app.state.verification_service = service
    return app


def test_jwks_outage_preserves_fresh_session_and_cooldown(flow):
    service, calls, _, _ = flow
    cookie = signed_session(service)
    attempts = []

    async def unavailable():
        attempts.append(True)
        raise TimeoutError("synthetic-provider-secret")

    service.validator = JWTValidator(issuer=service.validator.issuer, fetch_jwks=unavailable)
    with TestClient(app_for(service), base_url=service.public_origin) as client:
        client.cookies.set("__Host-studio_session", cookie)
        for _ in range(2):
            response = client.get("/api/session")
            assert response.status_code == 503
            assert "synthetic-provider-secret" not in response.text
            assert "set-cookie" not in response.headers
    assert len(attempts) == 1
    assert len(calls) == 1  # No refresh while access token is still valid.
    with service.transaction() as session:
        assert service.store.read_session(session, cookie)


def test_proven_wrong_issuer_remains_unauthorized(flow):
    service, _, _, _ = flow
    cookie = signed_session(service)
    service.validator.issuer = "https://other.example.test/auth/v1"
    with TestClient(app_for(service), base_url=service.public_origin) as client:
        client.cookies.set("__Host-studio_session", cookie)
        assert client.get("/api/session").status_code == 401


@pytest.mark.parametrize("operation", ["snapshot", "logout", "login", "resend", "verify"])
def test_db_wait_does_not_block_other_http_requests(flow, operation):
    service, _, _, _ = flow
    cookie = signed_session(service)
    transaction = service.transaction

    @contextmanager
    def slow_transaction():
        with transaction() as session:
            # Real PostgreSQL wait on the owned local test DB, not a time.sleep mock.
            session.execute(text("SELECT pg_sleep(0.4)"))
            yield session

    service.transaction = slow_transaction
    app = app_for(service)

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url=service.public_origin,
            headers={"Origin": service.public_origin},
            cookies={"__Host-studio_session": cookie},
        ) as client:
            request = {
                "snapshot": lambda: client.get("/api/session"),
                "logout": lambda: client.post(
                    "/api/auth/logout", headers={"X-CSRF-Token": service.csrf_token(cookie)}
                ),
                "login": lambda: client.post(
                    "/api/auth/login",
                    json={"email": "member@example.test", "password": "synthetic"},
                ),
                "resend": lambda: client.post(
                    "/api/auth/resend-verification", json={"email": "member@example.test"}
                ),
                "verify": lambda: client.post(
                    "/api/auth/verify-email",
                    json={"email": "member@example.test", "token": "123456"},
                ),
            }[operation]
            started = time.monotonic()
            pending = asyncio.create_task(request())
            try:
                await asyncio.sleep(0.025)
                health = await client.get("/health/live")
                elapsed = time.monotonic() - started
            finally:
                result = await pending
            assert health.status_code == 200
            assert result.status_code in {200, 202, 204}
            assert elapsed < 0.25, f"Unrelated request waited for DB: {elapsed:.3f}s"

    asyncio.run(run())


def test_cancel_during_refresh_commit_waits_before_releasing_lease(expired_session, monkeypatch):
    service, _, cookie, _, _ = expired_session
    entered = Event()
    finished = Event()
    complete = service.store.complete_refresh

    def delayed_complete(session, *args, **kwargs):
        entered.set()
        try:
            session.execute(text("SELECT pg_sleep(0.4)"))
            return complete(session, *args, **kwargs)
        finally:
            finished.set()

    async def refresh(_token):
        return refresh_support.refresh_response()

    service.gateway.refresh = refresh
    monkeypatch.setattr(service.store, "complete_refresh", delayed_complete)

    async def run():
        task = asyncio.create_task(service.session_profile(cookie))
        async with asyncio.timeout(3):
            while not entered.is_set():
                await asyncio.sleep(0.005)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        settled_at_cancellation = finished.is_set()
        # Drain even the old buggy implementation before this fixture tears down.
        assert await asyncio.to_thread(finished.wait, 3)
        assert settled_at_cancellation, "Cancellation released lease before DB work finished"

    asyncio.run(run())
    with service.transaction() as session:
        tokens = service.store.read_session(session, cookie)
        assert tokens.refresh_token.get_secret_value() == refresh_support.ROTATED_REFRESH
