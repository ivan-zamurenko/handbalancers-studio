import json
import logging

import httpx
import pytest
from fastapi.testclient import TestClient
from studio.auth.gateway import AuthGateway
from studio.auth.jwt import JWTValidator
from studio.auth.oauth import OAuthService
from studio.auth.supabase_adapter import SupabaseAuthAdapter
from studio.auth.token_store import TokenCipher, TokenStore
from studio.main import create_app

ORIGIN = "http://127.0.0.1:8765"
VALID = {
    "first_name": "Іван",
    "last_name": "Коваль",
    "email": "ivan@example.test",
    "password": "transient-password-123",
}


@pytest.fixture(autouse=True)
def isolate_quota_for_http_contract(monkeypatch):
    # These existing tests exercise HTTP/provider translation, not DB enforcement.
    # Real quota commits/concurrency/failure are covered in integration/auth/test_csrf_rate_limits.py.
    monkeypatch.setattr("studio.auth.service.quota", lambda *_args: None)


def client_for(status=200, body=None):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(status, json=body or {"id": "pending-auth-user"})

    app = create_app({"app_env": "local-test", "public_origin": ORIGIN})
    gateway = AuthGateway(
        SupabaseAuthAdapter(
            "https://auth.example.test",
            "key",
            client_factory=lambda **kw: httpx.AsyncClient(
                **kw, transport=httpx.MockTransport(respond)
            ),
        )
    )

    def forbidden_transaction():
        raise AssertionError("HTTP contract suite must not open a database")

    app.state.verification_service = OAuthService(
        auth_transaction=forbidden_transaction,
        store=TokenStore(
            TokenCipher("test", {"test": b"a" * 32}), allowed_return_paths=frozenset({"/plans"})
        ),
        gateway=gateway,
        validator=JWTValidator(issuer="https://auth.example.test/auth/v1"),
        supabase_url="https://auth.example.test",
        public_origin=ORIGIN,
        providers=frozenset(),
    )
    return TestClient(app, base_url=ORIGIN, headers={"origin": ORIGIN}), calls


def test_valid_signup_pending(caplog):
    client, calls = client_for()
    with caplog.at_level(logging.DEBUG):
        response = client.post("/api/auth/register", json=VALID)
    assert response.status_code == 202
    assert response.json() == {"state": "verification_pending"}
    assert "set-cookie" not in response.headers
    assert len(calls) == 1
    assert json.loads(calls[0].content)["password"] == VALID["password"]
    assert VALID["password"] not in caplog.text + response.text


@pytest.mark.parametrize(
    "change",
    [
        {"first_name": " "},
        {"last_name": ""},
        {"email": "bad"},
        {"password": "short"},
        {"role": "coach"},
    ],
)
def test_invalid_input_no_upstream(change):
    client, calls = client_for()
    response = client.post("/api/auth/register", json=VALID | change)
    assert response.status_code == 422
    assert not calls
    assert VALID["password"] not in response.text


def test_existing_email_generic():
    client, _ = client_for(422, {"error_code": "user_already_exists", "msg": "account exists"})
    response = client.post("/api/auth/register", json=VALID)
    assert response.status_code == 202
    assert response.json() == {"state": "verification_pending"}
    assert "set-cookie" not in response.headers


@pytest.mark.parametrize("status,expected", [(503, 503), (429, 429)])
def test_provider_unavailable(status, expected):
    client, _ = client_for(status, {"msg": VALID["password"]})
    response = client.post("/api/auth/register", json=VALID)
    assert response.status_code == expected
    if expected == 429:
        assert response.headers["retry-after"] == "60"
    assert "set-cookie" not in response.headers
    assert VALID["password"] not in response.text


def test_foreign_origin_refused():
    client, calls = client_for()
    response = client.post(
        "/api/auth/register", json=VALID, headers={"origin": "https://other.test"}
    )
    assert response.status_code == 403
    assert not calls
