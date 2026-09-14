import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from studio.models import BrowserSession, CheckoutAttempt, OnboardingProfile, Subscription
from studio.security import SESSION_COOKIE, token_hash
from tests.conftest import csrf_headers, register_demo

pytestmark = pytest.mark.postgres


def test_draft_survives_reload_and_is_isolated(client, answers, db_factory):
    headers = csrf_headers(client)
    cookie = client.cookies[SESSION_COOKIE]
    assert client.post("/api/onboarding", json=answers, headers=headers).status_code == 200
    assert client.get("/api/session").json()["onboarding"] == answers
    with db_factory() as db:
        assert db.get(BrowserSession, token_hash(cookie)).draft == answers
        assert db.get(BrowserSession, cookie) is None
    client.cookies.clear()
    assert client.get("/api/session").json()["onboarding"] is None


@pytest.mark.parametrize("registered", [False, True])
def test_legacy_onboarding_read_is_non_destructive(client, answers, db_factory, registered):
    headers = register_demo(client, answers) if registered else csrf_headers(client)
    state = client.get("/api/session").json()
    legacy = answers | {
        "primary_goal": "handstand",
        "equipment": ["wall"],
        "minutes": 20,
        "days": [0, 1, 2, 3, 4],
    }
    legacy.pop("minutes_plus")
    with db_factory() as db:
        if registered:
            row = db.get(OnboardingProfile, uuid.UUID(state["user"]["id"]))
            row.answers, row.schema_version = legacy, 1
        else:
            row = db.get(BrowserSession, token_hash(client.cookies[SESSION_COOKIE]))
            row.draft = legacy
        db.commit()
    current = client.get("/api/session").json()["onboarding"]
    assert current["days"] == legacy["days"] and current["minutes"] == 20
    assert current["minutes_plus"] is False
    assert "primary_goal" not in current and "equipment" not in current
    with db_factory() as db:
        if registered:
            profile = db.get(OnboardingProfile, uuid.UUID(state["user"]["id"]))
            assert profile.answers == legacy and profile.schema_version == 1
        else:
            assert (
                db.get(BrowserSession, token_hash(client.cookies[SESSION_COOKIE])).draft == legacy
            )
    # Only an explicit edit replaces legacy answers with the new questionnaire.
    assert client.post("/api/onboarding", json=answers, headers=headers).status_code == 200
    assert client.get("/api/session").json()["onboarding"] == answers
    if registered:
        with db_factory() as db:
            assert db.get(OnboardingProfile, uuid.UUID(state["user"]["id"])).schema_version == 2


@pytest.mark.parametrize("change", [{"days": [0, 1, 2, 3]}, {"minutes_plus": True}])
def test_new_onboarding_limits_rejected_without_overwriting_draft(client, answers, change):
    headers = csrf_headers(client)
    assert client.post("/api/onboarding", json=answers, headers=headers).status_code == 200
    assert client.post("/api/onboarding", json=answers | change, headers=headers).status_code == 422
    assert client.get("/api/session").json()["onboarding"] == answers


def test_csrf_and_owner_fields_rejected(client, answers):
    headers = csrf_headers(client)
    assert client.post("/api/onboarding", json=answers).status_code == 403
    assert (
        client.post(
            "/api/onboarding",
            json=answers,
            headers=[
                (b"Origin", str(client.base_url).rstrip("/").encode()),
                (b"X-CSRF-Token", b"\xff"),
            ],
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/onboarding", json=answers, headers=headers | {"Origin": "https://other.example"}
        ).status_code
        == 403
    )
    response = client.post(
        "/api/onboarding", json=answers | {"user_id": str(uuid.uuid4())}, headers=headers
    )
    assert response.status_code == 422
    assert all("input" not in detail for detail in response.json()["detail"])


def test_demo_full_flow_rotates_session_and_keeps_profile(client, answers, db_factory):
    initial = csrf_headers(client)
    old = client.cookies[SESSION_COOKIE]
    assert client.post("/api/onboarding", json=answers, headers=initial).status_code == 200
    assert (
        client.post("/api/preview/register", json={"name": "Олена"}, headers=initial).status_code
        == 200
    )
    assert client.cookies[SESSION_COOKIE] != old
    state = client.get("/api/session").json()
    assert state["user"]["is_demo"] is True
    assert state["onboarding"] == answers
    with db_factory() as db:
        assert db.get(BrowserSession, token_hash(old)) is None
        assert db.get(OnboardingProfile, uuid.UUID(state["user"]["id"])).answers == answers
        assert db.get(OnboardingProfile, uuid.UUID(state["user"]["id"])).schema_version == 2
    headers = csrf_headers(client)
    assert (
        client.post("/api/preview/pay", json={"plan_id": "plus"}, headers=headers).status_code
        == 409
    )
    assert (
        client.post(
            "/api/checkout", json={"plan_id": "plus", "price_cents": 1}, headers=headers
        ).status_code
        == 422
    )
    assert (
        client.post("/api/checkout", json={"plan_id": "plus"}, headers=headers).json()["url"]
        == "/checkout?plan=plus"
    )
    assert client.get("/api/session").json()["subscription"]["status"] == "pending"
    assert (
        client.post("/api/preview/pay", json={"plan_id": "plus"}, headers=headers).status_code
        == 200
    )
    assert (
        client.post("/api/preview/pay", json={"plan_id": "plus"}, headers=headers).status_code
        == 200
    )
    assert (
        client.post("/api/preview/pay", json={"plan_id": "pro"}, headers=headers).status_code == 409
    )
    membership = client.get("/api/session").json()["subscription"]
    assert {key: membership[key] for key in ("plan_id", "status", "is_demo")} == {
        "plan_id": "plus",
        "status": "active",
        "is_demo": True,
    }
    assert client.post("/api/logout", headers=headers).status_code == 200
    state = client.get("/api/session").json()
    assert state["user"] is None and state["onboarding"] is None


def test_preview_registration_cannot_impersonate_email(client, answers):
    headers = csrf_headers(client)
    client.post("/api/onboarding", json=answers, headers=headers)
    assert (
        client.post(
            "/api/preview/register",
            json={"name": "Test", "email": "person@example.invalid"},
            headers=headers,
        ).status_code
        == 422
    )


def test_demo_plan_change_expires_previous_pending_attempt(client, answers, db_factory):
    headers = register_demo(client, answers)
    client.post("/api/checkout", json={"plan_id": "essential"}, headers=headers)
    client.post("/api/checkout", json={"plan_id": "plus"}, headers=headers)
    with db_factory() as db:
        rows = db.scalars(select(CheckoutAttempt)).all()
        assert sorted((row.plan_id, row.status) for row in rows) == [
            ("essential", "expired"),
            ("plus", "pending"),
        ]
    assert (
        client.post("/api/preview/pay", json={"plan_id": "essential"}, headers=headers).status_code
        == 409
    )


def test_checkout_needs_authentication(client):
    headers = csrf_headers(client)
    assert (
        client.post("/api/checkout", json={"plan_id": "essential"}, headers=headers).status_code
        == 401
    )


def test_disabled_providers_and_billing_are_honest(client):
    state = client.get("/api/session").json()
    assert state["providers"] == {"google": False, "apple": False}
    assert state["payments_enabled"] is False
    response = client.get("/auth/google/login", follow_redirects=False)
    assert response.headers["location"] == "/register?auth_error=unavailable"
    assert client.post("/api/webhooks/stripe", content=b"{}").status_code == 503


def test_preview_denied_outside_loopback(client, settings, db_factory):
    from studio.main import create_app

    with TestClient(
        create_app(settings, db_factory), base_url=settings.base_url, client=("203.0.113.10", 50000)
    ) as remote:
        assert remote.post("/api/preview/register", json={"name": "x"}).status_code == 404


def test_preview_disabled_in_production(client, settings, db_factory):
    from studio.main import create_app

    production = settings.model_copy(
        update={
            "app_env": "production",
            "local_preview": False,
            "base_url": "https://studio.example",
        }
    )
    with TestClient(
        create_app(production, db_factory),
        base_url=production.base_url,
        client=("127.0.0.1", 50000),
    ) as public:
        assert public.post("/api/preview/register", json={"name": "x"}).status_code == 404
        assert public.post("/api/preview/pay", json={"plan_id": "plus"}).status_code == 404
        state = public.get("/api/session")
        assert "Secure" in state.headers["set-cookie"]
        assert state.json()["local_preview"] is False


def test_invalid_host_and_oversized_body_are_rejected(client):
    assert client.get("/health/live", headers={"Host": "attacker.example"}).status_code == 400
    response = client.post("/api/onboarding", content=b"x" * 40000)
    assert response.status_code == 413
    assert client.get("/health/live").json() == {"status": "ok"}


def test_active_membership_expires_on_the_server(client, answers, db_factory):
    from datetime import timedelta

    from studio.models import utcnow

    headers = register_demo(client, answers)
    client.post("/api/checkout", json={"plan_id": "essential"}, headers=headers)
    client.post("/api/preview/pay", json={"plan_id": "essential"}, headers=headers)
    with db_factory() as db:
        subscription = db.scalar(select(Subscription))
        subscription.current_period_end = utcnow() - timedelta(seconds=1)
        db.commit()
    assert client.get("/api/session").json()["subscription"]["status"] == "expired"


def test_stripe_signature_is_checked_against_raw_body(client, settings, monkeypatch):
    import hashlib
    import hmac
    import json
    import time

    from pydantic import SecretStr

    import studio.api

    secret = "webhook-test-fixture-only"
    settings.stripe_secret_key = SecretStr("api-test-fixture-only")
    settings.stripe_webhook_secret = SecretStr(secret)
    for plan in ("essential", "plus", "pro", "pro_plus"):
        setattr(settings, "stripe_price_" + plan, "price_fixture_" + plan)
    received = []
    monkeypatch.setattr(
        studio.api, "process_webhook", lambda factory, event, gateway: received.append(event["id"])
    )
    timestamp = str(int(time.time()))
    body = json.dumps(
        {
            "id": "evt_fixture",
            "type": "checkout.session.completed",
            "created": int(timestamp),
            "data": {"object": {}},
        }
    ).encode()
    signature = hmac.new(
        secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    headers = {"Stripe-Signature": f"t={timestamp},v1={signature}"}
    assert client.post("/api/webhooks/stripe", content=body).status_code == 400
    assert (
        client.post("/api/webhooks/stripe", content=body + b" ", headers=headers).status_code == 400
    )
    assert client.post("/api/webhooks/stripe", content=body, headers=headers).status_code == 200
    assert received == ["evt_fixture"]


@pytest.mark.parametrize(
    "path", ["/static/js/app.js", "/static/js/views.js", "/static/css/studio.css"]
)
def test_mutable_frontend_assets_revalidate(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-cache"
    cached = client.get(path, headers={"If-None-Match": response.headers["etag"]})
    assert cached.status_code == 304
    assert cached.headers["cache-control"] == "no-cache"
