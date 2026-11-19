"""Server entry rules with real PostgreSQL/RLS, no browser state as authority."""

from contextlib import contextmanager

import pytest
from sqlalchemy.exc import OperationalError

from server.tests.integration.database.test_auth_storage import (  # noqa: F401
    database_engine,
    storage_db,
)
from server.tests.security.accounts import test_profile_preferences as support
from server.tests.security.accounts.test_onboarding_model import VALID

flow = support.flow
device = support.device


def complete(client):
    assert (
        client.patch(
            "/api/me/profile", json={"first_name": "Ivan", "last_name": "Koval"}
        ).status_code
        == 200
    )
    assert client.put("/api/me/onboarding", json=VALID).status_code == 200


def test_incomplete_repeat_login_cannot_bypass_dashboard(device):
    open_device, _, _ = device
    for client in [open_device(), open_device()]:
        result = client.get("/dashboard?lang=en", follow_redirects=False)
        assert result.status_code == 303
        assert result.headers["location"] == "/profile?lang=en"
        assert client.get("/?lang=en").status_code == 200  # public pages are not paid access


def test_completed_new_device_skips_onboarding_and_enters_dashboard(device):
    open_device, _, _ = device
    complete(open_device())
    client = open_device()
    result = client.get("/onboarding?lang=en", follow_redirects=False)
    assert result.status_code == 303 and result.headers["location"] == "/dashboard?lang=en"
    result = client.get("/dashboard?lang=en")
    assert result.status_code == 200
    assert "No workout assigned yet" in result.text
    assert "data-start-workout" not in result.text
    assert "no-store" in result.headers["cache-control"]


@pytest.mark.parametrize("invalid", [False, True])
def test_dashboard_requires_valid_session(device, invalid):
    open_device, _, _ = device
    client = open_device()
    client.cookies.clear()
    if invalid:
        client.cookies.set("__Host-studio_session", "invalid")
    result = client.get("/dashboard?lang=uk", follow_redirects=False)
    assert result.status_code == 303
    assert result.headers["location"] == "/login?lang=uk"


def test_completion_db_failure_fails_closed(device):
    open_device, _, _ = device
    client = open_device()
    complete(client)

    @contextmanager
    def unavailable(actor):
        raise OperationalError("hidden", {}, Exception("offline"))
        yield

    client.app.state.web_transaction = unavailable
    assert client.get("/dashboard", follow_redirects=False).status_code == 503
    assert client.get("/api/session").json()["setup_required"] is None


def test_missing_locale_survives_redirect_for_browser_display_preference(device):
    open_device, _, _ = device
    client = open_device()
    result = client.get("/dashboard", follow_redirects=False)
    assert result.headers["location"] == "/profile"


def test_google_default_callback_enters_guarded_dashboard(device):
    from urllib.parse import parse_qs, urlsplit

    open_device, _, _ = device
    client = open_device()
    response = client.post("/api/auth/oauth/google/start", json={})
    assert response.status_code == 200
    callback = parse_qs(urlsplit(response.json()["authorization_url"]).query)["redirect_to"][0]
    result = client.get(callback + "&code=synthetic-code", follow_redirects=False)
    assert result.status_code == 303 and result.headers["location"] == "/dashboard"
    result = client.get("/dashboard", follow_redirects=False)
    assert result.headers["location"] == "/profile"
    # A new login rotates the session; the previous CSRF token must not authorize writes.
    assert client.patch("/api/me/profile", json={"first_name": "Ivan"}).status_code == 403
    client.headers["X-CSRF-Token"] = client.get("/api/session").json()["csrf_token"]
    complete(client)
    assert client.get("/dashboard").status_code == 200
