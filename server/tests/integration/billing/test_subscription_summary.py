"""Payment UI reads owned projection; neither browser selection nor redirect grants access."""

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


def test_summary_and_member_routes(device):
    open_device, db, auth_id = device
    client = open_device()
    client.app.state.checkout_service = CheckoutService(
        transaction=lambda: role_session(db, "studio_worker"),
        web_transaction=client.app.state.web_transaction,
        gateway=Provider(),
        origin=str(client.base_url).rstrip("/"),
    )
    result = client.get("/api/me/subscription")
    assert result.status_code == 200
    assert result.headers["cache-control"] == "no-store"
    assert result.json() == {
        "subscription": None,
        "active_attempt": None,
        "last_attempt": None,
        "trial_available": True,
        "portal_available": False,
    }
    assert client.get("/subscription", follow_redirects=False).headers["location"] == "/profile"
    client.patch("/api/me/profile", json={"first_name": "Synthetic", "last_name": "Billing"})
    client.put(
        "/api/me/onboarding",
        json={
            "goal_codes": ["fitness"],
            "self_reported_level": 1,
            "session_minutes": 30,
            "weekdays": [1],
            "expected_revision": 0,
        },
    )
    assert client.get("/subscription").status_code == 200
    # Foreign/missing attempt cannot disclose a status page.
    assert client.get("/billing/checkout/00000000-0000-4000-8000-000000000099").status_code == 404
    with db.begin() as c:
        c.execute(
            text(
                "INSERT INTO studio.billing_customers(user_id,provider_customer_id) SELECT id,'cus_summary' FROM studio.users WHERE auth_user_id=:a"
            ),
            {"a": auth_id},
        )
        c.execute(
            text(
                "INSERT INTO studio.subscriptions(user_id,provider_subscription_id,plan_code,status,current_period_start,current_period_end) SELECT user_id,'sub_summary','pro','active',now()-interval '1 day',now()+interval '10 days' FROM studio.billing_customers WHERE provider_customer_id='cus_summary'"
            )
        )
    try:
        result = client.get("/api/me/subscription").json()
        assert result["subscription"]["plan_code"] == "pro"
        assert result["portal_available"] is True
        assert "provider_subscription_id" not in result["subscription"]
        # A different server actor sees none of this owner's data.
        from uuid import UUID

        from studio.billing.summary import subscription_summary
        from studio.shared.context import Actor

        foreign = subscription_summary(client.app.state.checkout_service, Actor(UUID(int=99)))
        assert foreign["subscription"] is None and foreign["portal_available"] is False
        client.cookies.clear()
        assert client.get("/api/me/subscription").status_code == 401
        assert client.get("/subscription", follow_redirects=False).headers["location"] == "/login"
    finally:
        with db.begin() as c:
            c.execute(
                text(
                    "DELETE FROM studio.subscriptions WHERE provider_subscription_id='sub_summary'"
                )
            )
            c.execute(
                text(
                    "DELETE FROM studio.billing_customers WHERE provider_customer_id='cus_summary'"
                )
            )
