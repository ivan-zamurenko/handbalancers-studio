"""Authenticated, bounded history uses the web role and hides provider details."""

from uuid import UUID

from sqlalchemy import text
from studio.billing.checkout import CheckoutService
from studio.shared.context import Actor

from server.tests.integration.billing.test_checkout_attempts import Provider
from server.tests.integration.database.test_auth_storage import (  # noqa: F401
    database_engine,
    storage_db,
)
from server.tests.security.accounts import test_profile_preferences as support
from server.tests.support.actors import role_session

flow = support.flow
device = support.device


def test_history_api_owner_pagination_and_no_store(device):
    open_device, db, auth_id = device
    client = open_device()
    service = CheckoutService(
        transaction=lambda: role_session(db, "studio_worker"),
        web_transaction=client.app.state.web_transaction,
        gateway=Provider(),
        origin=str(client.base_url).rstrip("/"),
    )
    client.app.state.checkout_service = service
    response = client.get("/api/me/payments")
    assert response.status_code == 200
    assert response.json() == {"payments": [], "next_cursor": None}
    assert response.headers["cache-control"] == "no-store"
    with db.begin() as c:
        owner = c.scalar(text("SELECT id FROM studio.users WHERE auth_user_id=:a"), {"a": auth_id})
        c.execute(
            text(
                "INSERT INTO studio.billing_customers(user_id,provider_customer_id) VALUES(:u,'cus_api')"
            ),
            {"u": owner},
        )
        for i in range(3):
            c.execute(
                text("""INSERT INTO studio.payments
(id,user_id,provider_payment_id,provider_invoice_id,provider_payment_intent_id,
provider_customer_id,provider_subscription_id,provider_charge_id,plan_code,amount_minor,
currency,paid_at,livemode)
VALUES(:id,:u,:p,:invoice,:pi,'cus_api','sub_api',:charge,'pro',17999,'eur',:paid,false)"""),
                {
                    "id": UUID(int=i + 1),
                    "u": owner,
                    "p": f"inpay_api_{i}",
                    "invoice": f"in_api_{i}",
                    "pi": f"pi_api_{i}",
                    "charge": f"ch_api_{i}",
                    "paid": "2026-11-22T12:00:00Z",
                },
            )
    try:
        first = client.get("/api/me/payments?limit=2").json()
        assert len(first["payments"]) == 2 and first["next_cursor"]
        assert first["payments"][0]["id"] == str(UUID(int=3))
        second = client.get(
            "/api/me/payments", params={"limit": 2, "before": first["next_cursor"]}
        ).json()
        assert [x["id"] for x in second["payments"]] == [str(UUID(int=1))]
        assert second["next_cursor"] is None
        item = first["payments"][0]
        assert item["amount_minor"] == 17999 and item["status"] == "paid"
        assert item["refunded_minor"] == 0 and item["refunds"] == []
        assert not any(key.startswith("provider_") for key in item)
        assert client.get("/api/me/payments?limit=101").status_code == 422
        assert client.get("/api/me/payments?before=bad").status_code == 422
        from studio.billing.payments import payment_history

        foreign = payment_history(
            service.web_transaction,
            Actor(UUID(int=999)),
            limit=2,
            before=UUID(first["next_cursor"]),
        )
        assert foreign == {"payments": [], "next_cursor": None}
        client.cookies.clear()
        assert client.get("/api/me/payments").status_code == 401
    finally:
        with db.begin() as c:
            c.execute(text("DELETE FROM studio.payments WHERE user_id=:u"), {"u": owner})
            c.execute(text("DELETE FROM studio.billing_customers WHERE user_id=:u"), {"u": owner})
