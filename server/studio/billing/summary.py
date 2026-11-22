"""Read only the current actor's billing projection and recoverable intent."""

from sqlalchemy import text

from studio.billing.checkout import CheckoutService, view
from studio.shared.context import Actor


def subscription_summary(service: CheckoutService, actor: Actor) -> dict:
    with service.transaction() as session:
        params = {"u": actor.user_id}
        subscription = (
            session.execute(
                text(
                    "SELECT plan_code,status,current_period_start,current_period_end FROM studio.subscriptions WHERE user_id=:u"
                ),
                params,
            )
            .mappings()
            .one_or_none()
        )
        attempt = (
            session.execute(
                text(
                    "SELECT * FROM studio.checkout_attempts WHERE user_id=:u AND state IN ('creating','open','pending','needs_reconcile')"
                ),
                params,
            )
            .mappings()
            .one_or_none()
        )
        latest = (
            session.execute(
                text(
                    "SELECT * FROM studio.checkout_attempts WHERE user_id=:u ORDER BY created_at DESC,id DESC LIMIT 1"
                ),
                params,
            )
            .mappings()
            .one_or_none()
        )
        claim = session.scalar(
            text("SELECT state FROM studio.trial_claims WHERE user_id=:u"), params
        )
        customer = session.scalar(
            text("SELECT 1 FROM studio.billing_customers WHERE user_id=:u"), params
        )
        return {
            "subscription": dict(subscription) if subscription else None,
            "active_attempt": view(attempt) if attempt else None,
            "last_attempt": view(latest) if latest else None,
            "trial_available": claim not in {"reserved", "claimed"},
            "portal_available": bool(customer),
        }
