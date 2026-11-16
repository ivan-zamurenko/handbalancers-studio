"""S04-06: own profile + theme preference over HTTP, real PostgreSQL/RLS as studio_web."""

import asyncio
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from studio.main import create_app

from server.tests.integration.auth import test_oauth_flow as flow_support
from server.tests.integration.database.test_auth_storage import (  # noqa: F401
    database_engine,
    storage_db,
)
from server.tests.support.actors import role_session

flow = flow_support.flow


@pytest.fixture
def device(flow):
    service, _, db, auth_id = flow

    def open_device():
        start = service.start("google", "/plans")
        result = asyncio.run(
            service.finish("google", start.attempt, start.binding.get_secret_value(), "code")
        )
        app = create_app({"app_env": "test", "public_origin": service.public_origin})
        app.state.oauth_service = service
        app.state.web_transaction = lambda actor: role_session(db, "studio_web", actor.user_id)
        client = TestClient(
            app, base_url=service.public_origin, headers={"Origin": service.public_origin}
        )
        client.cookies.set("__Host-studio_session", result.cookie.get_secret_value())
        client.headers["X-CSRF-Token"] = client.get("/api/session").json()["csrf_token"]
        return client

    return open_device, db, auth_id


def test_editable_fields_only(device):
    open_device, db, auth_id = device
    client = open_device()
    for forbidden in (
        {"role": "coach"},
        {"email": "x@example.test"},
        {"auth_user_id": str(auth_id)},
    ):
        response = client.patch("/api/me/profile", json={"first_name": "Іван", **forbidden})
        assert response.status_code == 422
    with db.connect() as conn:
        row = conn.execute(
            text("SELECT role, first_name FROM studio.users WHERE auth_user_id=:a"), {"a": auth_id}
        ).one()
    assert tuple(row) == ("member", None)
    no_csrf = client.patch(
        "/api/me/profile", json={"first_name": "Іван"}, headers={"X-CSRF-Token": "bad"}
    )
    assert no_csrf.status_code == 403
    ok = client.patch("/api/me/profile", json={"first_name": "Іван"})
    assert ok.status_code == 200 and ok.json()["first_name"] == "Іван"
    assert ok.json()["role"] == "member"


def test_preferences_revision_conflict(device):
    open_device, _, _ = device
    phone, laptop = open_device(), open_device()
    assert phone.get("/api/me/preferences").json() == {"theme_preference": "auto", "revision": 0}
    first = phone.patch(
        "/api/me/preferences", json={"theme_preference": "dark", "expected_revision": 0}
    )
    assert first.status_code == 200 and first.json() == {"theme_preference": "dark", "revision": 1}
    stale = laptop.patch(
        "/api/me/preferences", json={"theme_preference": "light", "expected_revision": 0}
    )
    assert stale.status_code == 409
    assert stale.json()["current"] == {"theme_preference": "dark", "revision": 1}
    assert laptop.get("/api/me/preferences").json() == {"theme_preference": "dark", "revision": 1}
    bad = laptop.patch(
        "/api/me/preferences", json={"theme_preference": "neon", "expected_revision": 1}
    )
    assert bad.status_code == 422


def test_profile_complete_required(device):
    open_device, _, _ = device
    client = open_device()
    assert client.get("/api/session").json()["user"]["profile_complete"] is False
    response = client.patch("/api/me/profile", json={"first_name": "Іван", "last_name": "Петренко"})
    assert response.status_code == 200 and response.json()["profile_complete"] is True
    assert client.get("/api/session").json()["user"]["profile_complete"] is True


def test_other_user_rows_invisible(device):
    # RLS: preferences row of another profile is neither readable nor writable as studio_web.
    open_device, db, _ = device
    client = open_device()
    client.patch("/api/me/preferences", json={"theme_preference": "dark", "expected_revision": 0})
    stranger = UUID("00000000-0000-4000-8000-000000000077")
    with role_session(db, "studio_web", stranger) as session:
        assert session.scalar(text("SELECT count(*) FROM studio.user_preferences")) == 0
        updated = session.execute(
            text("UPDATE studio.user_preferences SET theme_preference='light'")
        ).rowcount
    assert updated == 0
