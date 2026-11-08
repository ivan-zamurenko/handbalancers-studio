"""Exercise HTTP boundaries with real parsing, including chunked oversized input."""

import asyncio
import base64
import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from studio.main import create_app
from studio.settings import Settings


@pytest.mark.parametrize("length", [None, b"1", b"65537"])
def test_body_limit_counts_bytes_without_trusting_content_length(length):
    app = create_app({"app_env": "test"})
    calls = []

    def probe(body: dict):
        calls.append(body)
        return {"ok": True}

    app.add_api_route("/api/auth/probe", probe, methods=["POST"])
    chunks = [b'{"value":"' + b"x" * 32768, b"x" * 32768 + b'"}']
    headers = [(b"content-type", b"application/json")]
    if length is not None:
        headers.append((b"content-length", length))
    messages = []

    async def receive():
        body = chunks.pop(0)
        return {"type": "http.request", "body": body, "more_body": bool(chunks)}

    async def send(message):
        messages.append(message)

    asyncio.run(
        app(
            {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": "POST",
                "scheme": "http",
                "path": "/api/auth/probe",
                "raw_path": b"/api/auth/probe",
                "query_string": b"",
                "root_path": "",
                "headers": headers,
                "client": ("127.0.0.1", 1234),
                "server": ("testserver", 80),
            },
            receive,
            send,
        )
    )
    assert messages[0]["status"] == 413
    assert calls == []
    payload = json.loads(b"".join(m.get("body", b"") for m in messages))
    assert payload["error"]["code"] == "content_too_large"
    assert dict(messages[0]["headers"])[b"cache-control"] == b"no-store"


def test_small_auth_body_still_reaches_normal_validation():
    app = create_app({"app_env": "test"})
    with TestClient(app) as client:
        assert client.post("/api/auth/login", json={}).status_code == 422


def test_api_schema_remains_available_without_cdn_documentation_pages():
    with TestClient(create_app({"app_env": "test"})) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/redoc").status_code == 404
        assert client.get("/openapi.json").status_code == 200


@pytest.mark.parametrize(
    "path", ["/login", "/api/session", "/missing", "/static/css/base.css", "/broken"]
)
def test_security_headers_cover_success_errors_and_static(path):
    app = create_app({"app_env": "test"})

    def broken():
        raise RuntimeError("synthetic-sensitive-error")

    app.add_api_route("/broken", broken)
    with TestClient(app) as client:
        response = client.get(path)
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    csp = response.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in csp
    assert "script-src 'self'" in csp
    assert "unsafe-inline" not in csp
    assert "strict-transport-security" not in response.headers


def test_https_deployment_sets_hsts():
    app = create_app(
        {
            "app_env": "production",
            "public_origin": "https://studio.example.test",
            "token_encryption_key": base64.b64encode(b"t" * 32).decode(),
        }
    )
    with TestClient(app, base_url="https://studio.example.test") as client:
        assert client.get("/login").headers["strict-transport-security"] == "max-age=31536000"


@pytest.mark.parametrize("environment", ["production", "staging"])
@pytest.mark.parametrize("mode", [None, "disable", "allow", "prefer", "require", "verify-ca"])
def test_deployed_auth_rejects_unverified_database_tls(environment, mode):
    config = auth_config(environment)
    if mode:
        config["auth_database_url"] += "?sslmode=" + mode
    with pytest.raises(ValidationError):
        Settings.model_validate(config)


def auth_config(environment):
    return {
        "app_env": environment,
        "public_origin": "https://studio.example.test",
        "token_encryption_key": base64.b64encode(b"t" * 32).decode(),
        "auth_email_enabled": True,
        "supabase_url": "https://auth.example.test",
        "supabase_publishable_key": "synthetic-public-key",
        "auth_database_url": "postgresql+psycopg://auth:synthetic@db.example.test/studio",
    }


def test_verified_database_tls_and_local_development_remain_usable():
    production = auth_config("production")
    production["auth_database_url"] += "?sslmode=verify-full&sslrootcert=/trusted/ca.crt"
    assert Settings.model_validate(production).app_env == "production"
    assert Settings.model_validate(auth_config("local-dev")).app_env == "local-dev"


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_deployment_rejects_untrusted_host_and_hides_schema(environment):
    app = create_app(
        {
            "app_env": environment,
            "public_origin": "https://studio.example.test",
            "token_encryption_key": base64.b64encode(b"t" * 32).decode(),
        }
    )
    with TestClient(app, base_url="https://studio.example.test") as client:
        assert client.get("/login").status_code == 200
        for host in (
            "attacker.test",
            "studio.example.test.attacker.test",
            "www.studio.example.test",
        ):
            response = client.get(
                "/login/",
                headers={
                    "Host": host,
                    "X-Forwarded-Host": "studio.example.test",
                },
                follow_redirects=False,
            )
            assert response.status_code == 400
            assert "location" not in response.headers
            assert response.headers["x-content-type-options"] == "nosniff"
        assert client.get("/openapi.json").status_code == 404
