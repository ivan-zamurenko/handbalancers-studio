"""Real DB/crypto/JWT; only remote Supabase exchange is a synthetic HTTP boundary."""

import asyncio
import base64
import hashlib
import time
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from sqlalchemy import text

from server.tests.integration.database.test_auth_storage import storage_db, database_engine  # noqa: F401
from server.tests.support.actors import role_session
from server.tests.unit.auth.test_auth_gateway import gateway_for
from studio.auth.jwt import JWTValidator
from studio.auth.token_store import TokenCipher, TokenStore, StoreError
from tools import local_stack


@pytest.fixture
def flow(storage_db):
    from studio.auth.oauth import OAuthService

    auth_id = uuid4()
    local_stack.execute_local_sql(
        local_stack.verify_container("test"),
        f"\\connect {storage_db.url.database}\nINSERT INTO auth.users VALUES ('{auth_id}');",
    )
    key = ec.generate_private_key(ec.SECP256R1())
    jwk = jwt.algorithms.ECAlgorithm.to_jwk(key.public_key(), as_dict=True)
    jwk.update(kid="test", alg="ES256", use="sig")

    async def keys():
        return {"keys": [jwk]}

    validator = JWTValidator(issuer="https://auth.example.test/auth/v1", fetch_jwks=keys)
    calls = []
    token = jwt.encode(
        {
            "sub": str(auth_id),
            "session_id": str(uuid4()),
            "aud": "authenticated",
            "iss": validator.issuer,
            "iat": int(time.time()),
            "exp": int(time.time()) + 300,
        },
        key,
        algorithm="ES256",
        headers={"kid": "test"},
    )

    def exchange(request):
        calls.append(request)
        return httpx.Response(
            200,
            json={
                "access_token": token,
                "refresh_token": "synthetic-refresh",
                "user": {
                    "id": str(auth_id),
                    "email_confirmed_at": "2026-10-01T00:00:00Z",
                    "user_metadata": {"role": "coach"},
                },
            },
        )

    service = OAuthService(
        auth_transaction=lambda: role_session(storage_db, "studio_auth_runtime"),
        store=TokenStore(
            TokenCipher("v1", {"v1": b"a" * 32}), allowed_return_paths=frozenset({"/plans"})
        ),
        gateway=gateway_for(exchange),
        validator=validator,
        supabase_url="https://auth.example.test",
        public_origin="https://studio.example.test",
        providers=frozenset({"google", "apple"}),
    )
    return service, calls, storage_db, auth_id


def test_independent_pkce_and_allowed_return(flow):
    service, calls, _, _ = flow
    first = service.start("google", "/plans")
    second = service.start("apple", "/plans")
    q1 = parse_qs(urlsplit(first.authorization_url).query)
    q2 = parse_qs(urlsplit(second.authorization_url).query)
    assert q1["code_challenge_method"] == ["s256"]
    assert q1["code_challenge"] != q2["code_challenge"]
    assert "state" not in q1 and "code_verifier" not in q1
    assert first.binding != second.binding
    for provider, path in [
        ("github", "/plans"),
        ("google", "https://evil.test"),
        ("google", "//evil.test"),
    ]:
        with pytest.raises(ValueError):
            service.start(provider, path)
    assert not calls


def test_callback_binding_replay_verified_session(flow):
    service, calls, db, auth_id = flow
    start = service.start("google", "/plans")
    with pytest.raises(StoreError):
        asyncio.run(service.finish("google", start.attempt, "wrong-browser", "code"))
    assert not calls
    result = asyncio.run(
        service.finish("google", start.attempt, start.binding.get_secret_value(), "code")
    )
    assert result.return_path == "/plans"
    with pytest.raises(StoreError):
        asyncio.run(
            service.finish("google", start.attempt, start.binding.get_secret_value(), "code")
        )
    assert len(calls) == 1
    with db.connect() as c:
        row = c.execute(
            text("SELECT role,first_name,last_name FROM studio.users WHERE auth_user_id=:id"),
            {"id": auth_id},
        ).one()
        assert row == ("member", None, None)
        assert (
            c.scalar(
                text("SELECT count(*) FROM studio_private.web_sessions WHERE user_id=:id"),
                {"id": result.user_id},
            )
            == 1
        )
    with role_session(db, "studio_auth_runtime") as s:
        stored = service.store.read_session(s, result.cookie.get_secret_value())
        assert stored.user_id == result.user_id
    q = parse_qs(urlsplit(start.authorization_url).query)
    import json

    verifier = json.loads(calls[0].content)["code_verifier"]
    assert q["code_challenge"] == [
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    ]


def test_apple_missing_name_same_identity_no_duplicate(flow):
    service, calls, db, auth_id = flow
    results = []
    for _ in range(2):
        attempt = service.start("apple", "/plans")
        results.append(
            asyncio.run(
                service.finish("apple", attempt.attempt, attempt.binding.get_secret_value(), "code")
            )
        )
    assert results[0].user_id == results[1].user_id
    assert not results[0].profile_complete
    with db.connect() as c:
        assert (
            c.scalar(
                text("SELECT count(*) FROM studio.users WHERE auth_user_id=:id"), {"id": auth_id}
            )
            == 1
        )


def test_http_start_callback_cookie_and_current_session(flow):
    from fastapi.testclient import TestClient
    from studio.main import create_app

    service, calls, db, _ = flow
    app = create_app({"app_env": "test", "public_origin": "https://studio.example.test"})
    app.state.oauth_service = service
    client = TestClient(app, base_url="https://studio.example.test")
    start = client.post(
        "/api/auth/oauth/google/start",
        json={"return_to": "/plans"},
        headers={"Origin": service.public_origin},
    )
    assert start.status_code == 200
    url = start.json()["authorization_url"]
    callback = parse_qs(urlsplit(url).query)["redirect_to"][0]
    response = client.get(callback + "&code=synthetic", follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"] == "/plans"
    cookie = response.headers.get_list("set-cookie")[0]
    assert (
        "__Host-studio_session=" in cookie
        and "HttpOnly" in cookie
        and "Secure" in cookie
        and "SameSite=lax" in cookie
        and "Domain=" not in cookie
    )
    snapshot = client.get("/api/session")
    assert snapshot.status_code == 200 and snapshot.json()["authenticated"]
    assert snapshot.json()["user"]["role"] == "member"
    assert "access_token" not in snapshot.text and "refresh_token" not in snapshot.text
    with db.begin() as c:
        c.execute(
            text("UPDATE studio.users SET is_active=false WHERE id=:id"),
            {"id": snapshot.json()["user"]["id"]},
        )
    assert client.get("/api/session").status_code == 401


def test_cancel_timeout_consume_and_expiry(flow):
    from studio.auth.gateway import AuthFailure, AuthFailureKind

    service, calls, db, _ = flow
    cancelled = service.start("apple", "/plans")
    service.cancel("apple", cancelled.attempt, cancelled.binding.get_secret_value())
    with pytest.raises(StoreError):
        asyncio.run(
            service.finish("apple", cancelled.attempt, cancelled.binding.get_secret_value(), "code")
        )
    expired = service.start("google", "/plans")
    with db.begin() as c:
        c.execute(
            text(
                "UPDATE studio_private.auth_attempts SET expires_at=now()-interval '1 second' WHERE state_hash=:hash"
            ),
            {"hash": hashlib.sha256(expired.attempt.encode()).hexdigest()},
        )
    with pytest.raises(StoreError):
        asyncio.run(
            service.finish("google", expired.attempt, expired.binding.get_secret_value(), "code")
        )
    assert not calls
    pending = service.start("google", "/plans")

    async def timeout(*args):
        raise AuthFailure(AuthFailureKind.TIMEOUT)

    service.gateway.oauth_exchange = timeout
    with pytest.raises(AuthFailure):
        asyncio.run(
            service.finish("google", pending.attempt, pending.binding.get_secret_value(), "code")
        )
    with pytest.raises(StoreError):
        asyncio.run(
            service.finish("google", pending.attempt, pending.binding.get_secret_value(), "code")
        )


def test_concurrent_callback_only_one_exchange(flow):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    service, calls, _, _ = flow
    attempt = service.start("google", "/plans")
    barrier = Barrier(2)

    def callback():
        barrier.wait(timeout=5)
        try:
            return asyncio.run(
                service.finish(
                    "google", attempt.attempt, attempt.binding.get_secret_value(), "code"
                )
            )
        except StoreError:
            return None

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: callback(), range(2)))
    assert sum(result is not None for result in results) == 1
    assert len(calls) == 1


def test_invalid_identity_no_profile_or_session(flow):
    service, calls, db, auth_id = flow

    async def bad_exchange(*args):
        return {
            "access_token": "invalid-jwt",
            "refresh_token": "synthetic",
            "user": {"id": str(auth_id), "email_confirmed_at": "2026-10-01"},
        }

    service.gateway.oauth_exchange = bad_exchange
    from studio.auth.jwt import InvalidIdentity

    attempt = service.start("google", "/plans")
    with pytest.raises(InvalidIdentity):
        asyncio.run(
            service.finish("google", attempt.attempt, attempt.binding.get_secret_value(), "code")
        )
    with db.connect() as c:
        assert (
            c.scalar(
                text("SELECT count(*) FROM studio.users WHERE auth_user_id=:id"), {"id": auth_id}
            )
            == 0
        )


def test_runtime_rejects_migration_owner(flow):
    from studio.auth.runtime import check_auth_role

    service, calls, db, auth_id = flow
    from sqlalchemy.orm import Session

    with Session(db) as session, session.begin(), pytest.raises(ValueError):
        check_auth_role(session)
    with role_session(db, "studio_auth_runtime") as session:
        check_auth_role(session)


def test_rate_limit_bounds_attempts(flow):
    from studio.auth.oauth import OAuthRateLimited

    service, _, _, _ = flow
    for _ in range(10):
        service.start("google", "/plans", client_key="one-client")
    with pytest.raises(OAuthRateLimited):
        service.start("google", "/plans", client_key="one-client")
    service.start("google", "/plans", client_key="other-client")


def test_logout_csrf_and_revocation(flow):
    from fastapi.testclient import TestClient
    from studio.main import create_app

    service, _, _, _ = flow
    app = create_app({"app_env": "test", "public_origin": "https://studio.example.test"})
    app.state.oauth_service = service
    client = TestClient(app, base_url=service.public_origin)
    start = client.post(
        "/api/auth/oauth/apple/start", headers={"Origin": service.public_origin}, json={}
    )
    callback = parse_qs(urlsplit(start.json()["authorization_url"]).query)["redirect_to"][0]
    client.get(callback + "&code=synthetic", follow_redirects=False)
    cookie = client.cookies.get("__Host-studio_session")
    csrf = client.get("/api/session").json()["csrf_token"]
    assert (
        client.post("/api/auth/logout", headers={"Origin": service.public_origin}).status_code
        == 403
    )
    result = client.post(
        "/api/auth/logout", headers={"Origin": service.public_origin, "X-CSRF-Token": csrf}
    )
    assert result.status_code == 204
    assert client.get("/api/session").json() == {"authenticated": False}
    client.cookies.set("__Host-studio_session", cookie)
    assert client.get("/api/session").status_code == 401


def test_logout_stays_revoked_during_upstream_outage(flow):
    from studio.auth.gateway import AuthFailure, AuthFailureKind

    service, _, db, _ = flow
    start = service.start("google", "/plans")
    result = asyncio.run(
        service.finish("google", start.attempt, start.binding.get_secret_value(), "code")
    )

    async def offline(*args):
        raise AuthFailure(AuthFailureKind.TIMEOUT)

    service.gateway.logout = offline
    asyncio.run(service.logout(result.cookie.get_secret_value()))
    with role_session(db, "studio_auth_runtime") as session, pytest.raises(StoreError):
        service.store.read_session(session, result.cookie.get_secret_value())


def test_second_login_rotates_old_cookie_and_inactive_denied(flow):
    from studio.auth.jwt import InvalidIdentity

    service, _, db, auth_id = flow
    start = service.start("google", "/plans")
    old = asyncio.run(
        service.finish("google", start.attempt, start.binding.get_secret_value(), "code")
    )
    start = service.start("google", "/plans")
    new = asyncio.run(
        service.finish(
            "google",
            start.attempt,
            start.binding.get_secret_value(),
            "code",
            old.cookie.get_secret_value(),
        )
    )
    assert new.cookie != old.cookie
    with role_session(db, "studio_auth_runtime") as s, pytest.raises(StoreError):
        service.store.read_session(s, old.cookie.get_secret_value())
    with db.begin() as c:
        c.execute(
            text("UPDATE studio.users SET is_active=false WHERE auth_user_id=:id"), {"id": auth_id}
        )
    start = service.start("google", "/plans")
    with pytest.raises(InvalidIdentity):
        asyncio.run(
            service.finish("google", start.attempt, start.binding.get_secret_value(), "code")
        )
