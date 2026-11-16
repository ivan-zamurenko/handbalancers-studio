"""S04-02: /auth/callback HTTP contract on real PostgreSQL; only Supabase HTTP is synthetic.

Kept in a DB suite (not server/tests/contracts, which CI runs without a database).
"""

import logging
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from studio.main import create_app

from server.tests.integration.auth import test_oauth_flow as flow_support
from server.tests.integration.database.test_auth_storage import (  # noqa: F401
    database_engine,
    storage_db,
)

flow = flow_support.flow
SESSION = "__Host-studio_session"
CODE = "synthetic-provider-code-7f3a"


def browser(service):
    app = create_app({"app_env": "test", "public_origin": service.public_origin})
    app.state.oauth_service = service
    return TestClient(app, base_url=service.public_origin)


def start(client, service, return_to="/plans"):
    response = client.post(
        "/api/auth/oauth/google/start",
        json={"return_to": return_to},
        headers={"Origin": service.public_origin},
    )
    assert response.status_code == 200
    return parse_qs(urlsplit(response.json()["authorization_url"]).query)["redirect_to"][0]


def sessions(db, auth_id):
    with db.connect() as conn:
        return conn.scalar(
            text(
                "SELECT count(*) FROM studio_private.web_sessions s "
                "JOIN studio.users u ON u.id = s.user_id WHERE u.auth_user_id = :id"
            ),
            {"id": auth_id},
        )


def profiles(db, auth_id):
    with db.connect() as conn:
        return conn.scalar(
            text("SELECT count(*) FROM studio.users WHERE auth_user_id=:id"), {"id": auth_id}
        )


def test_replay_rejected(flow):
    service, calls, db, auth_id = flow
    client = browser(service)
    callback = start(client, service)
    # Keep the binding cookie so the replay is rejected for consumption, not a missing cookie.
    binding = {k: v for k, v in client.cookies.items() if "studio_oauth_" in k}
    assert len(binding) == 1
    first = client.get(callback + "&code=" + CODE, follow_redirects=False)
    assert first.status_code == 303 and first.headers["location"] == "/plans"
    assert sessions(db, auth_id) == 1
    client.cookies.clear()
    for name, value in binding.items():
        client.cookies.set(name, value, domain="studio.example.test", path="/")
    replay = client.get(callback + "&code=" + CODE, follow_redirects=False)
    assert replay.status_code == 303
    assert replay.headers["location"] == "/login?oauth=failed"
    assert SESSION + "=" not in "".join(replay.headers.get_list("set-cookie"))
    assert len(calls) == 1
    assert sessions(db, auth_id) == 1


def test_missing_browser_binding(flow):
    service, calls, db, auth_id = flow
    callback = start(browser(service), service)
    attacker = browser(service)
    stolen = attacker.get(callback + "&code=" + CODE, follow_redirects=False)
    assert stolen.status_code == 303
    assert stolen.headers["location"] == "/login?oauth=failed"
    assert SESSION + "=" not in "".join(stolen.headers.get_list("set-cookie"))
    assert stolen.headers["cache-control"] == "no-store"
    assert attacker.get("/api/session").json() == {"authenticated": False}
    assert not calls
    assert profiles(db, auth_id) == 0 and sessions(db, auth_id) == 0


def test_cancel_is_recoverable(flow):
    service, calls, db, auth_id = flow
    client = browser(service)
    callback = start(client, service)
    cancelled = client.get(callback + "&error=access_denied", follow_redirects=False)
    assert cancelled.status_code == 303
    assert cancelled.headers["location"] == "/login?oauth=cancelled"
    assert "studio_oauth_" in cancelled.headers["set-cookie"]
    assert "Max-Age=0" in cancelled.headers["set-cookie"]
    page = client.get("/login?oauth=cancelled&lang=en")
    assert page.status_code == 200
    assert 'role="alert"' in page.text and "Sign-in cancelled. You can try again." in page.text
    # The same browser can start again and finish normally.
    retry = client.get(start(client, service) + "&code=" + CODE, follow_redirects=False)
    assert retry.headers["location"] == "/plans"
    assert len(calls) == 1 and sessions(db, auth_id) == 1


def test_verified_user_provisioned_once(flow, caplog):
    service, calls, db, auth_id = flow
    caplog.set_level(logging.DEBUG)
    for _ in range(2):
        client = browser(service)
        done = client.get(start(client, service) + "&code=" + CODE, follow_redirects=False)
        assert done.headers["location"] == "/plans"
        snapshot = client.get("/api/session").json()
        assert snapshot["authenticated"] and snapshot["user"]["role"] == "member"
    assert profiles(db, auth_id) == 1
    with db.connect() as conn:
        tables = conn.scalars(
            text(
                "SELECT table_schema || '.' || table_name FROM information_schema.tables "
                "WHERE table_name ~* 'users?$' AND table_schema LIKE 'studio%'"
            )
        ).all()
    assert tables == ["studio.users"]
    assert len(calls) == 2
    # Records of the in-process test browser's own requests are not server logs.
    browser_side = "HTTP Request: GET " + service.public_origin
    server = [r for r in caplog.records if not r.getMessage().startswith(browser_side)]
    assert any(r.name == "studio.access" for r in server)
    # Inspect every record attribute (message, args and `extra` fields used by formatters).
    assert not any(CODE in str(value) for r in server for value in vars(r).values())
    assert all(CODE not in str(call.url) for call in calls)


@pytest.mark.parametrize("return_to", ["https://evil.test/", "//evil.test", "/admin"])
def test_redirect_only_allowed_local_path(flow, return_to):
    service, calls, _, _ = flow
    client = browser(service)
    response = client.post(
        "/api/auth/oauth/google/start",
        json={"return_to": return_to},
        headers={"Origin": service.public_origin},
    )
    assert response.status_code == 422 and "set-cookie" not in response.headers
    assert not calls
