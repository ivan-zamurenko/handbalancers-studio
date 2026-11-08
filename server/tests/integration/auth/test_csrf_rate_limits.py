"""Real isolated PostgreSQL quotas; only the external provider is synthetic."""

import copy
import hashlib
import hmac
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from studio.auth.oauth import OAuthRateLimited
from studio.auth.verification import quota
from studio.main import create_app

from server.tests.integration.auth import test_oauth_flow as flow_support
from server.tests.integration.database.test_auth_storage import (  # noqa: F401
    database_engine,
    storage_db,
)
from server.tests.support.actors import role_session
from server.tests.unit.auth.test_auth_gateway import gateway_for

flow = flow_support.flow
SIGNUP = {
    "first_name": "Test",
    "last_name": "Member",
    "email": "member@example.test",
    "password": "synthetic-password-123",
}


def signup_app(service):
    app = create_app({"app_env": "test", "public_origin": service.public_origin})
    app.state.oauth_service = app.state.verification_service = service
    app.state.auth_gateway = service.gateway
    return app


def bucket(service, value):
    return hmac.new(service.secret, value.encode(), hashlib.sha256).hexdigest()


def test_rate_limit_atomic(flow):
    service, _, engine, _ = flow
    calls = []

    def provider(request):
        calls.append(request)
        return httpx.Response(200, json={"id": "pending"})

    service.gateway = gateway_for(provider)
    # Independent app instances share the DB and the deployment secret, not process locks.
    apps = [signup_app(copy.copy(service)) for _ in range(20)]
    barrier = Barrier(20, timeout=15)

    def request(index):
        with TestClient(
            apps[index], base_url=service.public_origin, client=("192.0.2.1", 5000 + index)
        ) as client:
            barrier.wait()
            return client.post(
                "/api/auth/register",
                json=SIGNUP | {"email": f"member-{index}@example.test"},
                headers={"Origin": service.public_origin, "X-Forwarded-For": f"198.51.100.{index}"},
            )

    with ThreadPoolExecutor(max_workers=20) as pool:
        responses = list(pool.map(request, range(20)))
    assert [r.status_code for r in responses].count(202) == 10
    assert [r.status_code for r in responses].count(429) == 10
    assert len(calls) == 10
    for response in responses:
        assert "set-cookie" not in response.headers
        assert response.headers["cache-control"] == "no-store"
        if response.status_code == 429:
            assert response.headers["retry-after"] == "60"
    with engine.connect() as connection:
        assert (
            connection.scalar(
                text(
                    "SELECT attempts FROM studio_private.auth_rate_limits WHERE bucket_hash=:bucket"
                ),
                {"bucket": bucket(service, "register:ip:192.0.2.1")},
            )
            == 11
        )


def test_registration_account_budget_survives_provider_failure_and_new_ip(flow):
    service, _, engine, _ = flow
    calls = []

    def unavailable(request):
        calls.append(request)
        return httpx.Response(503, json={})

    service.gateway = gateway_for(unavailable)
    for index, expected in enumerate([503, 429]):
        with TestClient(
            signup_app(service), base_url=service.public_origin, client=(f"192.0.2.{index}", 5000)
        ) as client:
            response = client.post(
                "/api/auth/register", json=SIGNUP, headers={"Origin": service.public_origin}
            )
        assert response.status_code == expected
    assert len(calls) == 1
    # Expiry is derived from window_start; reset does not need a duplicate expires_at column.
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE studio_private.auth_rate_limits SET window_start=clock_timestamp()-interval '61 seconds' WHERE bucket_hash=:bucket"
            ),
            {"bucket": bucket(service, "register:email:" + SIGNUP["email"])},
        )
    quota(service, "register", SIGNUP["email"], "new-client")


def test_rate_limit_atomic_account_budget_across_clients(flow):
    service, _, _, _ = flow
    barrier = Barrier(20, timeout=15)

    def attempt(index):
        barrier.wait()
        try:
            quota(copy.copy(service), "password-login", "same@example.test", f"client-{index}")
        except OAuthRateLimited:
            return False
        return True

    with ThreadPoolExecutor(max_workers=20) as pool:
        assert sum(pool.map(attempt, range(20))) == 10


def test_rate_limit_storage_is_private_and_transactional(flow):
    service, _, engine, _ = flow
    quota(service, "register", "private@example.test", "192.0.2.8")
    with engine.connect() as connection:
        hashes = (
            connection.execute(text("SELECT bucket_hash FROM studio_private.auth_rate_limits"))
            .scalars()
            .all()
        )
        assert all(len(value) == 64 and set(value) <= set("0123456789abcdef") for value in hashes)
        assert connection.scalar(
            text(
                "SELECT relrowsecurity FROM pg_class WHERE oid='studio_private.auth_rate_limits'::regclass"
            )
        )
        for role in ["anon", "authenticated", "studio_web", "studio_worker"]:
            assert not connection.scalar(
                text(
                    "SELECT has_table_privilege(:role,'studio_private.auth_rate_limits','SELECT,INSERT,UPDATE,DELETE,TRUNCATE')"
                ),
                {"role": role},
            )
    from studio.auth.rate_limit import allow_start

    rolled_back = bucket(service, "rollback")
    with pytest.raises(RuntimeError), role_session(engine, "studio_auth_runtime") as session:
        assert allow_start(session, rolled_back)
        raise RuntimeError("intentional abort")
    with engine.connect() as connection:
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM studio_private.auth_rate_limits WHERE bucket_hash=:bucket"
                ),
                {"bucket": rolled_back},
            )
            == 0
        )


def test_stricter_configured_limits_are_enforced(flow):
    from studio.auth.rate_limit import AuthLimits

    service, _, _, _ = flow
    service.limits = AuthLimits(client=2, account=1)
    quota(service, "password-login", "same@example.test", "one")
    with pytest.raises(OAuthRateLimited):
        quota(service, "password-login", "same@example.test", "two")
    # Client budget is committed even when the account budget rejects.
    quota(service, "password-login", "next@example.test", "two")
    with pytest.raises(OAuthRateLimited):
        quota(service, "password-login", "third@example.test", "two")
    service.start("google", "/plans", client_key="oauth")
    service.start("google", "/plans", client_key="oauth")
    with pytest.raises(OAuthRateLimited):
        service.start("google", "/plans", client_key="oauth")


def test_stricter_worker_cannot_reopen_exhausted_budget(flow):
    from studio.auth.rate_limit import allow_start

    service, _, engine, _ = flow
    shared = bucket(service, "rolling-config")
    for _ in range(10):
        with role_session(engine, "studio_auth_runtime") as session:
            assert allow_start(session, shared, limit=10)
    with role_session(engine, "studio_auth_runtime") as session:
        assert not allow_start(session, shared, limit=2)
    with role_session(engine, "studio_auth_runtime") as session:
        assert not allow_start(session, shared, limit=10)
    with engine.connect() as connection:
        assert (
            connection.scalar(
                text(
                    "SELECT attempts FROM studio_private.auth_rate_limits WHERE bucket_hash=:bucket"
                ),
                {"bucket": shared},
            )
            == 11
        )
