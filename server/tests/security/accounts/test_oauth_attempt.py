"""S04-01: browser-bound OAuth attempt with per-attempt PKCE on real PostgreSQL storage."""

import base64
import hashlib
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient
from studio.main import create_app

from server.tests.integration.auth import test_oauth_flow as flow_support
from server.tests.integration.database.test_auth_storage import (  # noqa: F401
    database_engine,
    storage_db,
)

flow = flow_support.flow


def challenge_of(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def query(start):
    return parse_qs(urlsplit(start.authorization_url).query)


def consumed_verifier(service, start, provider="google"):
    with service.transaction() as session:
        pending = service.store.consume_attempt(
            session, start.attempt, provider=provider, binding=start.binding.get_secret_value()
        )
    return pending.verifier.get_secret_value()


def test_pkce_verifier_per_attempt(flow):
    service, calls, _, _ = flow
    first, second = service.start("google", "/plans"), service.start("google", "/plans")
    v1, v2 = consumed_verifier(service, first), consumed_verifier(service, second)
    assert v1 != v2 and len(v1) >= 43 and len(v2) >= 43
    assert query(first)["code_challenge"] == [challenge_of(v1)]
    assert query(second)["code_challenge"] == [challenge_of(v2)]
    assert query(first)["code_challenge_method"] == ["s256"]
    assert first.attempt != second.attempt
    assert first.binding.get_secret_value() != second.binding.get_secret_value()
    for start in (first, second):
        binding = start.binding.get_secret_value()
        assert binding != start.attempt and start.attempt not in binding
        assert "code_verifier" not in query(start) and "state" not in query(start)
    assert not calls


@pytest.mark.parametrize(
    "return_to",
    [
        "https://evil.test/plans",
        "//evil.test/plans",
        "/\\evil.test",
        "/plans/../admin",
        "/admin",
        "",
        "/plans\r\nLocation: https://evil.test",
    ],
)
def test_return_path_allowlist(flow, return_to):
    service, calls, _, _ = flow
    with pytest.raises(ValueError):
        service.start("google", return_to)
    redirect = query(service.start("google", "/plans"))["redirect_to"][0]
    parts = urlsplit(redirect)
    assert (parts.scheme, parts.netloc, parts.path) == (
        "https",
        "studio.example.test",
        "/auth/callback",
    )
    assert not calls


@pytest.mark.parametrize("provider", ["github", "GOOGLE", "google ", "apple", "", "azure"])
def test_provider_allowlist(flow, provider):
    service, calls, _, _ = flow
    google_only = type(service).__new__(type(service))
    google_only.__dict__.update(service.__dict__, providers=frozenset({"google"}))
    with pytest.raises(ValueError):
        google_only.start(provider, "/plans")
    app = create_app({"app_env": "test", "public_origin": service.public_origin})
    app.state.oauth_service = google_only
    with TestClient(app, base_url=service.public_origin) as client:
        response = client.post(
            f"/api/auth/oauth/{provider}/start",
            headers={"Origin": service.public_origin},
            json={"return_to": "/plans"},
        )
        control = client.post(
            "/api/auth/oauth/google/start",
            headers={"Origin": service.public_origin},
            json={"return_to": "/plans"},
        )
    assert control.status_code == 200 and "authorization_url" in control.json()
    assert "studio_oauth_" in control.headers["set-cookie"]
    assert response.status_code in {404, 405, 422, 503}
    assert "authorization_url" not in response.text
    assert "set-cookie" not in response.headers
    assert not calls


def test_no_shared_mutable_client(flow):
    service, calls, _, _ = flow
    with ThreadPoolExecutor(max_workers=8) as pool:
        # Distinct browsers; per-client start quota is covered by rate-limit tests.
        starts = list(
            pool.map(
                lambda i: service.start("google", "/plans", client_key=f"browser-{i}"), range(16)
            )
        )
    assert len({start.attempt for start in starts}) == 16
    assert len({start.binding.get_secret_value() for start in starts}) == 16
    assert len({query(start)["code_challenge"][0] for start in starts}) == 16
    for start in starts:
        params = query(start)
        assert f"attempt={start.attempt}" in params["redirect_to"][0]
        assert params["code_challenge"] == [challenge_of(consumed_verifier(service, start))]
    assert not calls
