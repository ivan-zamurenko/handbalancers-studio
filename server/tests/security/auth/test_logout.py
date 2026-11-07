"""Origin/CSRF must reject before any DB or upstream logout operation."""

from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from studio.auth.jwt import JWTValidator
from studio.auth.oauth import OAuthService
from studio.auth.token_store import TokenCipher, TokenStore
from studio.main import create_app

from server.tests.unit.auth.test_auth_gateway import gateway_for


@pytest.mark.parametrize(
    "origin,csrf,cookie",
    [
        (None, "valid", True),
        ("https://evil.test", "valid", True),
        ("https://studio.example.test", None, True),
        ("https://studio.example.test", "wrong", True),
        ("https://studio.example.test", "valid", False),
    ],
)
def test_logout_requires_origin_and_csrf_before_database(origin, csrf, cookie):
    @contextmanager
    def forbidden_transaction():
        raise AssertionError("Rejected logout must not open a DB transaction")
        yield

    def forbidden_provider(_request):
        raise AssertionError("Rejected logout must not contact provider")

    service = OAuthService(
        auth_transaction=forbidden_transaction,
        store=TokenStore(
            TokenCipher("test", {"test": b"a" * 32}), allowed_return_paths=frozenset({"/plans"})
        ),
        gateway=gateway_for(forbidden_provider),
        validator=JWTValidator(issuer="https://auth.example.test/auth/v1"),
        supabase_url="https://auth.example.test",
        public_origin="https://studio.example.test",
        providers=frozenset(),
    )
    app = create_app({"app_env": "test", "public_origin": service.public_origin})
    app.state.oauth_service = service
    with TestClient(app, base_url=service.public_origin) as client:
        if cookie:
            client.cookies.set("__Host-studio_session", "synthetic-cookie")
        headers = {}
        if origin:
            headers["Origin"] = origin
        if csrf:
            headers["X-CSRF-Token"] = (
                service.csrf_token("synthetic-cookie") if csrf == "valid" else csrf
            )
        response = client.post("/api/auth/logout", headers=headers)
    assert response.status_code == 403
    assert "set-cookie" not in response.headers
    assert response.headers["cache-control"] == "no-store"
