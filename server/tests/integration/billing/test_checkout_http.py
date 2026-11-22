"""Checkout uses existing real session/CSRF/profile boundary and isolated DB."""

from studio.billing.checkout import CheckoutService

from server.tests.integration.billing.test_checkout_attempts import Provider
from server.tests.integration.database.test_auth_storage import (  # noqa: F401
    database_engine,
    storage_db,
)
from server.tests.security.accounts import test_profile_preferences as support
from server.tests.support.actors import role_session

flow = support.flow
device = support.device


def test_checkout_http_guards_and_status(device):
    open_device, db, _ = device
    client = open_device()
    client.app.state.checkout_service = CheckoutService(
        transaction=lambda: role_session(db, "studio_worker"),
        web_transaction=client.app.state.web_transaction,
        gateway=Provider(),
        origin=str(client.base_url).rstrip("/"),
    )
    body = {"plan_code": "essential", "terms_version": "test-v1"}
    headers = {"Idempotency-Key": "http-test-key"}
    assert client.post("/api/checkout", json=body, headers=headers).status_code == 403
    assert (
        client.patch(
            "/api/me/profile", json={"first_name": "Synthetic", "last_name": "Tester"}
        ).status_code
        == 200
    )
    assert (
        client.put(
            "/api/me/onboarding",
            json={
                "goal_codes": ["fitness"],
                "self_reported_level": 1,
                "session_minutes": 30,
                "weekdays": [1],
                "expected_revision": 0,
            },
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/checkout", json={**body, "price_id": "price_evil"}, headers=headers
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/checkout", json=body, headers={**headers, "X-CSRF-Token": "0" * 64}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/checkout", json=body, headers={**headers, "Origin": "https://foreign.test"}
        ).status_code
        == 403
    )
    response = client.post("/api/checkout", json=body, headers=headers)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    url = "/api/me/checkout-attempts/" + response.json()["id"]
    assert client.get(url).json()["state"] == "open"
    assert (
        client.get("/api/me/checkout-attempts/00000000-0000-4000-8000-000000000099").status_code
        == 404
    )
    client.cookies.clear()
    assert client.get(url).status_code == 401
