"""Stripe is isolated here so API handlers cannot accidentally trust client pricing."""

from datetime import UTC, datetime, timedelta

import stripe
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from studio.models import CheckoutAttempt, Subscription, User, WebhookEvent, utcnow
from studio.plans import PLANS
from studio.settings import Settings


class BillingUnavailable(Exception):
    """Safe public failure; provider responses and credentials are not exposed."""


class StripeGateway:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.key = settings.stripe_secret_key.get_secret_value()

    def create_checkout(self, attempt: CheckoutAttempt) -> tuple[str, str]:
        try:
            price = stripe.Price.retrieve(attempt.stripe_price_id, api_key=self.key)
            recurring = price.get("recurring") or {}
            if (
                not price.get("active")
                or price.get("unit_amount") != attempt.amount_cents
                or price.get("currency", "").upper() != attempt.currency
                or recurring.get("interval") != "month"
                or recurring.get("interval_count") != 1
            ):
                raise BillingUnavailable("Configured Stripe price does not match the plan")
            session = stripe.checkout.Session.create(
                api_key=self.key,
                idempotency_key=f"studio-checkout-{attempt.id}",
                mode="subscription",
                # Keep the initial flow synchronous; asynchronous bank debits need another lifecycle.
                payment_method_types=["card"],
                line_items=[{"price": attempt.stripe_price_id, "quantity": 1}],
                client_reference_id=str(attempt.user_id),
                metadata={"checkout_id": str(attempt.id), "user_id": str(attempt.user_id)},
                subscription_data={"metadata": {"user_id": str(attempt.user_id)}},
                success_url=f"{self.settings.base_url}/dashboard?checkout=success",
                cancel_url=f"{self.settings.base_url}/checkout?plan={attempt.plan_id}&canceled=1",
            )
            return session.id, session.url
        except BillingUnavailable:
            raise
        except stripe.StripeError:
            raise BillingUnavailable("Payment provider is temporarily unavailable") from None

    def checkout(self, session_id: str):
        return stripe.checkout.Session.retrieve(
            session_id,
            api_key=self.key,
            expand=["line_items", "subscription"],
        )

    def subscription(self, subscription_id: str):
        return stripe.Subscription.retrieve(subscription_id, api_key=self.key)

    def expire_checkout(self, session_id: str):
        try:
            current = stripe.checkout.Session.retrieve(session_id, api_key=self.key)
            if current.get("status") == "expired":
                return
            if current.get("status") != "open":
                raise BillingUnavailable("Previous checkout is already being processed")
            stripe.checkout.Session.expire(session_id, api_key=self.key)
        except stripe.StripeError:
            raise BillingUnavailable("Previous checkout could not be closed") from None


def active_subscription(subscription: Subscription | None) -> bool:
    return bool(
        subscription
        and subscription.status in {"active", "trialing"}
        and subscription.current_period_end
        and subscription.current_period_end > utcnow()
    )


def begin_checkout(
    db: Session, settings: Settings, user: User, plan_id: str, gateway: StripeGateway
):
    if user.is_demo and not settings.preview_enabled:
        raise HTTPException(403, "Demo accounts cannot make real purchases")
    if not user.is_demo and not settings.payments_enabled:
        raise HTTPException(503, "Payments have not been configured yet")
    # Lock the owner to serialize double-clicks and competing plan selections.
    db.execute(select(User).where(User.id == user.id).with_for_update())
    subscription = db.get(Subscription, user.id)
    if active_subscription(subscription):
        raise HTTPException(409, "A membership is already active")
    attempt = db.scalar(
        select(CheckoutAttempt)
        .where(
            CheckoutAttempt.user_id == user.id,
            CheckoutAttempt.status == "pending",
            CheckoutAttempt.is_demo == user.is_demo,
        )
        .order_by(CheckoutAttempt.created_at.desc())
        .limit(1)
    )
    if attempt and (
        attempt.plan_id != plan_id or attempt.created_at <= utcnow() - timedelta(hours=23)
    ):
        if not user.is_demo:
            if not attempt.stripe_session_id:
                raise HTTPException(409, "A checkout is being prepared. Please try again shortly")
            try:
                gateway.expire_checkout(attempt.stripe_session_id)
            except BillingUnavailable:
                raise HTTPException(
                    409, "The previous checkout must finish before changing plans"
                ) from None
        attempt.status = "expired"
        attempt = None
    if attempt is None:
        plan = PLANS[plan_id]
        attempt = CheckoutAttempt(
            user_id=user.id,
            plan_id=plan_id,
            amount_cents=plan.price_cents,
            currency=plan.currency,
            is_demo=user.is_demo,
            stripe_price_id=None if user.is_demo else settings.stripe_prices[plan_id],
        )
        db.add(attempt)
        if subscription is None:
            db.add(Subscription(user_id=user.id, plan_id=plan_id, is_demo=user.is_demo))
        elif subscription.status not in {"active", "trialing"}:
            subscription.plan_id = plan_id
            subscription.status = "pending"
        db.commit()
    if user.is_demo:
        return f"/checkout?plan={plan_id}"
    if attempt.checkout_url:
        return attempt.checkout_url
    try:
        stripe_id, url = gateway.create_checkout(attempt)
    except BillingUnavailable:
        raise HTTPException(503, "Unable to start checkout. Please try again later") from None
    attempt.stripe_session_id = stripe_id
    attempt.checkout_url = url
    db.commit()
    return url


def demo_payment(db: Session, user: User, plan_id: str):
    if not user.is_demo:
        raise HTTPException(403, "Demo checkout requires a local demo account")
    db.execute(select(User).where(User.id == user.id).with_for_update())
    attempt = db.scalar(
        select(CheckoutAttempt)
        .where(
            CheckoutAttempt.user_id == user.id,
            CheckoutAttempt.plan_id == plan_id,
            CheckoutAttempt.is_demo.is_(True),
            CheckoutAttempt.status == "pending",
        )
        .order_by(CheckoutAttempt.created_at.desc())
        .limit(1)
    )
    subscription = db.get(Subscription, user.id)
    if (
        active_subscription(subscription)
        and subscription.is_demo
        and subscription.plan_id == plan_id
    ):
        return  # Repeated demo clicks are idempotent.
    if active_subscription(subscription):
        raise HTTPException(409, "A membership is already active")
    if attempt is None or subscription is None:
        raise HTTPException(409, "Choose a plan before the demo checkout")
    attempt.status = "paid"
    subscription.plan_id = plan_id
    subscription.status = "active"
    subscription.is_demo = True
    subscription.current_period_end = utcnow() + timedelta(days=30)
    db.commit()


def period_end(provider_subscription) -> datetime | None:
    # Stripe moved period dates into subscription items in newer API versions.
    timestamp = provider_subscription.get("current_period_end")
    if not timestamp:
        items = provider_subscription.get("items", {}).get("data", [])
        timestamp = min(
            (item["current_period_end"] for item in items if item.get("current_period_end")),
            default=None,
        )
    return datetime.fromtimestamp(timestamp, UTC) if timestamp else None


def apply_webhook(db: Session, event: dict, gateway: StripeGateway):
    """Store the event and entitlement in one transaction; failed processing is retryable."""
    inserted = db.execute(
        insert(WebhookEvent)
        .values(id=event["id"], event_type=event["type"])
        .on_conflict_do_nothing()
        .returning(WebhookEvent.id)
    ).scalar_one_or_none()
    if inserted is None:
        db.rollback()
        return
    kind = event["type"]
    payload = event["data"]["object"]
    created = int(event["created"])
    if kind == "checkout.session.completed":
        checkout = gateway.checkout(payload["id"])
        attempt = db.scalar(
            select(CheckoutAttempt)
            .where(
                CheckoutAttempt.stripe_session_id == checkout["id"],
            )
            .with_for_update()
        )
        if attempt is None:
            # Creation and webhook may race: request a provider retry until the ID is persisted.
            raise BillingUnavailable("Checkout is not ready for reconciliation")
        validate_paid_checkout(attempt, checkout)
        provider_sub = checkout["subscription"]
        subscription = db.get(Subscription, attempt.user_id, with_for_update=True)
        if subscription and created >= subscription.last_event_created:
            subscription.plan_id = attempt.plan_id
            subscription.is_demo = False
            subscription.stripe_subscription_id = provider_sub["id"]
            subscription.status = provider_sub["status"]
            subscription.current_period_end = period_end(provider_sub)
            subscription.last_event_created = created
        attempt.status = "paid"
    elif kind in {
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "invoice.paid",
        "invoice.payment_failed",
    }:
        sub_id = (
            payload.get("id")
            if kind.startswith("customer.subscription.")
            else payload.get("subscription")
        )
        if not sub_id:
            sub_id = payload.get("parent", {}).get("subscription_details", {}).get("subscription")
        if sub_id:
            subscription = db.scalar(
                select(Subscription)
                .where(
                    Subscription.stripe_subscription_id == sub_id,
                )
                .with_for_update()
            )
            if subscription and created >= subscription.last_event_created:
                current = gateway.subscription(sub_id)
                subscription.status = current["status"]
                subscription.current_period_end = period_end(current)
                subscription.last_event_created = created
    db.commit()


def validate_paid_checkout(attempt: CheckoutAttempt, checkout):
    lines = checkout.get("line_items", {}).get("data", [])
    metadata = checkout.get("metadata") or {}
    sub = checkout.get("subscription")
    if (
        attempt.is_demo
        or checkout.get("mode") != "subscription"
        or checkout.get("payment_status") != "paid"
        or checkout.get("client_reference_id") != str(attempt.user_id)
        or metadata.get("checkout_id") != str(attempt.id)
        or metadata.get("user_id") != str(attempt.user_id)
        or checkout.get("amount_total") != attempt.amount_cents
        or checkout.get("currency", "").upper() != attempt.currency
        or len(lines) != 1
        or lines[0].get("quantity") != 1
        or (lines[0].get("price") or {}).get("id") != attempt.stripe_price_id
        or not isinstance(sub, dict)
        or sub.get("status") not in {"active", "trialing"}
        or (sub.get("metadata") or {}).get("user_id") != str(attempt.user_id)
        or not period_end(sub)
        or period_end(sub) <= utcnow()
    ):
        raise BillingUnavailable("Payment does not match the pending membership")
