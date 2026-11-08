"""Reject ambiguous CSRF/Origin headers before DB or provider work."""

from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from studio.auth.jwt import JWTValidator
from studio.auth.oauth import OAuthService
from studio.auth.token_store import TokenCipher, TokenStore
from studio.main import create_app

from server.tests.unit.auth.test_auth_gateway import gateway_for

ORIGIN = "https://studio.example.test"
SIGNUP = {
    "first_name": "Test",
    "last_name": "Member",
    "email": "member@example.test",
    "password": "synthetic-password-123",
}


@pytest.fixture
def guarded():
    @contextmanager
    def forbidden_transaction():
        raise AssertionError("Rejected request must not access database")
        yield

    def forbidden_provider(_request):
        raise AssertionError("Rejected request must not contact provider")

    service = OAuthService(
        auth_transaction=forbidden_transaction,
        store=TokenStore(
            TokenCipher("test", {"test": b"a" * 32}), allowed_return_paths=frozenset({"/plans"})
        ),
        gateway=gateway_for(forbidden_provider),
        validator=JWTValidator(issuer="https://auth.example.test/auth/v1"),
        supabase_url="https://auth.example.test",
        public_origin=ORIGIN,
        providers=frozenset({"google"}),
    )
    app = create_app({"app_env": "test", "public_origin": ORIGIN})
    app.state.oauth_service = app.state.verification_service = service
    app.state.auth_gateway = service.gateway
    with TestClient(app, base_url=ORIGIN) as client:
        client.cookies.set("__Host-studio_session", "synthetic-cookie")
        yield client, service


@pytest.mark.parametrize("csrf", [None, b"wrong", b"\xff", b"x" * 65])
def test_csrf_missing_rejected(guarded, csrf):
    client, _ = guarded
    headers = [(b"origin", ORIGIN.encode())]
    if csrf is not None:
        headers.append((b"x-csrf-token", csrf))
    response = client.post("/api/auth/logout", headers=headers)
    assert response.status_code == 403
    assert "set-cookie" not in response.headers


def test_duplicate_csrf_rejected(guarded):
    client, service = guarded
    response = client.post(
        "/api/auth/logout",
        headers=[
            ("Origin", ORIGIN),
            ("X-CSRF-Token", service.csrf_token("synthetic-cookie")),
            ("X-CSRF-Token", "wrong"),
        ],
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    "path,body",
    [
        ("/api/auth/register", SIGNUP),
        ("/api/auth/login", {"email": SIGNUP["email"], "password": SIGNUP["password"]}),
        ("/api/auth/verify-email", {"email": SIGNUP["email"], "token": "123456"}),
        ("/api/auth/resend-verification", {"email": SIGNUP["email"]}),
        ("/api/auth/recovery/request", {"email": SIGNUP["email"]}),
        (
            "/api/auth/recovery/confirm",
            {"email": SIGNUP["email"], "token": "123456", "password": SIGNUP["password"]},
        ),
        ("/api/auth/oauth/google/start", {}),
        ("/api/auth/logout", {}),
    ],
)
@pytest.mark.parametrize(
    "origins", [[], ["https://evil.test"], ["null"], [ORIGIN, "https://evil.test"]]
)
def test_login_csrf_rejected(guarded, path, body, origins):
    client, service = guarded
    headers = [("Origin", value) for value in origins]
    headers.append(("X-CSRF-Token", service.csrf_token("synthetic-cookie")))
    response = client.post(path, json=body, headers=headers)
    assert response.status_code == 403
    assert "set-cookie" not in response.headers


def test_oauth_callback_exception_narrow(guarded):
    client, _ = guarded
    # A GET callback has its own state/binding checks, not the unsafe POST origin guard.
    response = client.get(
        "/auth/callback?attempt=invalid&provider=google&code=synthetic",
        headers={"Origin": "https://provider.test"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/login?oauth=failed"
    assert client.post("/auth/callback", json={}).status_code == 405
    assert (
        client.post(
            "/api/auth/oauth/google/start", json={}, headers={"Origin": "https://provider.test"}
        ).status_code
        == 403
    )


def test_registration_without_quota_runtime_fails_closed():
    calls = []

    def provider(request):
        calls.append(request)
        import httpx

        return httpx.Response(200, json={"id": "pending"})

    app = create_app({"app_env": "test", "public_origin": ORIGIN})
    app.state.auth_gateway = gateway_for(provider)
    with TestClient(app, base_url=ORIGIN) as client:
        response = client.post("/api/auth/register", json=SIGNUP, headers={"Origin": ORIGIN})
    assert response.status_code == 503
    assert not calls


def test_csrf_from_another_session_rejected(guarded):
    client, service = guarded
    response = client.post(
        "/api/auth/logout",
        headers={"Origin": ORIGIN, "X-CSRF-Token": service.csrf_token("another-cookie")},
    )
    assert response.status_code == 403
    assert response.headers["cache-control"] == "no-store"
    assert "set-cookie" not in response.headers


@pytest.mark.parametrize("value", [0, -1, 11])
def test_quota_configuration_cannot_disable_or_exceed_storage_bounds(value):
    from pydantic import ValidationError
    from studio.settings import Settings

    for name in ["auth_client_attempts_per_minute", "auth_account_attempts_per_minute"]:
        with pytest.raises(ValidationError):
            Settings.model_validate({"app_env": "test", name: value})


def test_quota_configuration_supports_stricter_defaults():
    from studio.settings import Settings

    config = Settings.model_validate(
        {
            "app_env": "test",
            "auth_client_attempts_per_minute": 3,
            "auth_account_attempts_per_minute": 2,
        }
    )
    assert config.auth_client_attempts_per_minute == 3
    assert config.auth_account_attempts_per_minute == 2


def test_runtime_uses_configured_quota_defaults():
    import base64

    from studio.auth.runtime import build_oauth
    from studio.settings import Settings

    service = build_oauth(
        Settings.model_validate(
            {
                "app_env": "test",
                "public_origin": ORIGIN,
                "auth_email_enabled": True,
                "auth_database_url": "postgresql+psycopg://test:synthetic@127.0.0.1:55322/postgres",
                "supabase_url": "https://auth.example.test",
                "supabase_publishable_key": "synthetic-public",
                "token_encryption_key": base64.b64encode(b"a" * 32).decode(),
                "auth_client_attempts_per_minute": 3,
                "auth_account_attempts_per_minute": 2,
            }
        )
    )
    assert service.limits.client == 3
    assert service.limits.account == 2
