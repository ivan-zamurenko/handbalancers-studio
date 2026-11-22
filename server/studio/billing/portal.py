"""Resolve the actor's customer locally before creating a short-lived portal link."""

from sqlalchemy import text

from studio.billing.checkout import CheckoutNotFound, CheckoutService
from studio.shared.context import Actor


def create_portal(service: CheckoutService, actor: Actor) -> dict[str, str]:
    with service.transaction() as session:
        customer = session.scalar(
            text("SELECT provider_customer_id FROM studio.billing_customers WHERE user_id=:u"),
            {"u": actor.user_id},
        )
        if customer is None:
            raise CheckoutNotFound()
    # No transaction or customer identifier is carried from the browser.
    return {"url": service.gateway.create_portal(customer, service.origin + "/subscription")}
