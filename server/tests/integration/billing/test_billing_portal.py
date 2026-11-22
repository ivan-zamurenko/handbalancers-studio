"""Portal sessions are bound to the authenticated local customer, never browser input."""

from sqlalchemy import text
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


def test_portal_owner_and_return_allowlist(device):
    open_device, db, auth_id = device
    client = open_device()
    provider = Provider()
    calls = []

    def portal(customer_id, return_url):
        calls.append((customer_id, return_url))
        return "https://billing.stripe.com/p/session/test_synthetic"

    provider.create_portal = portal
    client.app.state.checkout_service = CheckoutService(
        transaction=lambda: role_session(db, "studio_worker"),
        web_transaction=client.app.state.web_transaction,
        gateway=provider,
        origin=str(client.base_url).rstrip("/"),
    )
    result = client.post("/api/billing-portal", json={})
    assert result.status_code == 409
    assert result.json()["error"]["code"] == "checkout_required"
    assert calls == []
    with db.begin() as c:
        c.execute(
            text(
                "INSERT INTO studio.billing_customers(user_id,provider_customer_id) SELECT id,'cus_portal_owner' FROM studio.users WHERE auth_user_id=:a"
            ),
            {"a": auth_id},
        )
    try:
        for injection in (
            {"customer_id": "cus_foreign"},
            {"return_url": "https://foreign.test"},
            {"cancel": True},
        ):
            assert client.post("/api/billing-portal", json=injection).status_code == 422
        assert (
            client.post("/api/billing-portal", json={}, headers={"X-CSRF-Token": "bad"}).status_code
            == 403
        )
        assert (
            client.post(
                "/api/billing-portal", json={}, headers={"Origin": "https://foreign.test"}
            ).status_code
            == 403
        )
        response = client.post("/api/billing-portal", json={})
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["url"].startswith("https://billing.stripe.com/")
        assert calls == [("cus_portal_owner", str(client.base_url).rstrip("/") + "/subscription")]
        with db.connect() as c:
            assert c.scalar(text("SELECT count(*) FROM studio.subscriptions")) == 0
        client.cookies.clear()
        assert client.post("/api/billing-portal", json={}).status_code == 401
    finally:
        with db.begin() as c:
            c.execute(
                text(
                    "DELETE FROM studio.billing_customers WHERE provider_customer_id='cus_portal_owner'"
                )
            )
