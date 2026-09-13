import copy
import time
import uuid
from datetime import timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from studio.billing import (
    BillingUnavailable,
    StripeGateway,
    apply_webhook,
    begin_checkout,
    period_end,
    validate_paid_checkout,
)
from studio.models import CheckoutAttempt, Subscription, User, WebhookEvent, utcnow


@pytest.fixture
def paid_checkout():
    attempt = CheckoutAttempt(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        plan_id="plus",
        amount_cents=4999,
        currency="EUR",
        stripe_price_id="price_fixture",
        stripe_session_id="cs_fixture",
        is_demo=False,
    )
    checkout = {
        "id": "cs_fixture",
        "mode": "subscription",
        "payment_status": "paid",
        "client_reference_id": str(attempt.user_id),
        "amount_total": 4999,
        "currency": "eur",
        "metadata": {"checkout_id": str(attempt.id), "user_id": str(attempt.user_id)},
        "line_items": {"data": [{"quantity": 1, "price": {"id": "price_fixture"}}]},
        "subscription": {
            "id": "sub_fixture",
            "status": "active",
            "metadata": {"user_id": str(attempt.user_id)},
            "current_period_end": int(time.time()) + 3600,
        },
    }
    return attempt, checkout


@pytest.mark.parametrize(
    "change",
    [
        {"payment_status": "unpaid"},
        {"amount_total": 1},
        {"currency": "usd"},
        {"client_reference_id": "another-owner"},
        {"metadata": {}},
        {"line_items": {"data": [{"quantity": 1, "price": {"id": "other_price"}}]}},
        {"subscription": {"id": "sub_fixture", "status": "incomplete"}},
    ],
)
def test_payment_must_match_owner_and_server_price(paid_checkout, change):
    attempt, checkout = paid_checkout
    with pytest.raises(BillingUnavailable):
        validate_paid_checkout(attempt, checkout | change)


def test_valid_checkout_and_new_stripe_period_format(paid_checkout):
    attempt, checkout = paid_checkout
    validate_paid_checkout(attempt, checkout)
    subscription = checkout["subscription"]
    end = subscription.pop("current_period_end")
    subscription["items"] = {"data": [{"current_period_end": end}]}
    validate_paid_checkout(attempt, checkout)
    assert period_end(subscription).timestamp() == end


def test_gateway_checks_provider_price_and_limits_payment_methods(
    monkeypatch, settings, paid_checkout
):
    from types import SimpleNamespace

    import stripe

    attempt, _ = paid_checkout
    captured = {}

    def fake_price(*args, **kwargs):
        return {
            "active": True,
            "unit_amount": 4999,
            "currency": "eur",
            "recurring": {"interval": "month", "interval_count": 1},
        }

    def fake_create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(id="cs_fixture", url="https://checkout.stripe.com/c/pay/fixture")

    monkeypatch.setattr(stripe.Price, "retrieve", fake_price)
    monkeypatch.setattr(stripe.checkout.Session, "create", fake_create)
    StripeGateway(settings).create_checkout(attempt)
    assert captured["payment_method_types"] == ["card"]
    assert captured["line_items"] == [{"price": "price_fixture", "quantity": 1}]
    assert captured["client_reference_id"] == str(attempt.user_id)
    assert captured["idempotency_key"] == f"studio-checkout-{attempt.id}"
    monkeypatch.setattr(stripe.Price, "retrieve", lambda *args, **kwargs: {"active": False})
    with pytest.raises(BillingUnavailable):
        StripeGateway(settings).create_checkout(attempt)


class FakeGateway:
    def __init__(self, checkout):
        self.snapshot = checkout
        self.expired = []
        self.created = []

    def checkout(self, session_id):
        assert session_id == self.snapshot["id"]
        return copy.deepcopy(self.snapshot)

    def subscription(self, subscription_id):
        assert subscription_id == self.snapshot["subscription"]["id"]
        return copy.deepcopy(self.snapshot["subscription"])

    def create_checkout(self, attempt):
        self.created.append(attempt.id)
        return f"cs_{attempt.id}", f"https://checkout.stripe.com/c/pay/{attempt.id}"

    def expire_checkout(self, session_id):
        self.expired.append(session_id)


def seed_checkout(db, paid_checkout):
    attempt, checkout = paid_checkout
    db.add(User(id=attempt.user_id, name="Fixture", is_demo=False))
    db.flush()
    db.add(attempt)
    db.add(Subscription(user_id=attempt.user_id, plan_id="plus", status="pending", is_demo=False))
    db.commit()
    return attempt, checkout


def completion_event(checkout):
    return {
        "id": "evt_complete",
        "type": "checkout.session.completed",
        "created": 100,
        "data": {"object": {"id": checkout["id"]}},
    }


@pytest.mark.postgres
def test_webhook_deduplicates_and_old_events_cannot_reactivate(db_factory, paid_checkout):
    with db_factory() as db:
        attempt, checkout = seed_checkout(db, paid_checkout)
        gateway = FakeGateway(checkout)
        event = completion_event(checkout)
        apply_webhook(db, event, gateway)
        apply_webhook(db, event, gateway)
        assert db.scalar(select(func.count()).select_from(WebhookEvent)) == 1
        assert db.get(Subscription, attempt.user_id).status == "active"
        gateway.snapshot["subscription"]["status"] = "canceled"
        apply_webhook(
            db,
            {
                "id": "evt_cancel",
                "type": "customer.subscription.deleted",
                "created": 200,
                "data": {"object": {"id": "sub_fixture"}},
            },
            gateway,
        )
        assert db.get(Subscription, attempt.user_id).status == "canceled"
        gateway.snapshot["subscription"]["status"] = "active"
        apply_webhook(
            db,
            {
                "id": "evt_old",
                "type": "customer.subscription.updated",
                "created": 150,
                "data": {"object": {"id": "sub_fixture"}},
            },
            gateway,
        )
        assert db.get(Subscription, attempt.user_id).status == "canceled"


@pytest.mark.postgres
def test_failed_webhook_rolls_back_and_can_retry(db_factory, paid_checkout):
    with db_factory() as db:
        attempt, checkout = seed_checkout(db, paid_checkout)
        owner = attempt.user_id
        gateway = FakeGateway(checkout)
        gateway.snapshot["amount_total"] = 1
        with pytest.raises(BillingUnavailable):
            apply_webhook(db, completion_event(checkout), gateway)
        db.rollback()
        assert db.get(WebhookEvent, "evt_complete") is None
        assert db.get(Subscription, owner).status == "pending"
        gateway.snapshot["amount_total"] = 4999
        apply_webhook(db, completion_event(checkout), gateway)
        assert db.get(Subscription, owner).status == "active"


@pytest.mark.postgres
@pytest.mark.parametrize(
    "invoice",
    [
        {"subscription": "sub_fixture"},
        {"parent": {"subscription_details": {"subscription": "sub_fixture"}}},
    ],
)
def test_invoice_renewal_supports_old_and_new_stripe_shapes(db_factory, paid_checkout, invoice):
    with db_factory() as db:
        attempt, checkout = seed_checkout(db, paid_checkout)
        gateway = FakeGateway(checkout)
        apply_webhook(db, completion_event(checkout), gateway)
        end = int((utcnow() + timedelta(days=35)).timestamp())
        gateway.snapshot["subscription"]["current_period_end"] = end
        apply_webhook(
            db,
            {
                "id": "evt_renewal",
                "type": "invoice.paid",
                "created": 200,
                "data": {"object": invoice},
            },
            gateway,
        )
        assert db.get(Subscription, attempt.user_id).current_period_end.timestamp() == end


@pytest.mark.postgres
def test_checkout_reuses_same_plan_and_expires_previous_plan(db_factory, settings):
    from pydantic import SecretStr

    settings.stripe_secret_key = SecretStr("test-fixture-only")
    settings.stripe_webhook_secret = SecretStr("test-fixture-only")
    settings.stripe_price_essential = "price_essential"
    settings.stripe_price_plus = "price_plus"
    settings.stripe_price_pro = "price_pro"
    settings.stripe_price_pro_plus = "price_pro_plus"
    gateway = FakeGateway({})
    with db_factory() as db:
        user = User(name="Fixture", is_demo=False)
        db.add(user)
        db.commit()
        first = begin_checkout(db, settings, user, "essential", gateway)
        assert begin_checkout(db, settings, user, "essential", gateway) == first
        second = begin_checkout(db, settings, user, "plus", gateway)
        assert first != second and len(gateway.created) == 2 and len(gateway.expired) == 1
        rows = db.scalars(select(CheckoutAttempt)).all()
        assert sorted(row.status for row in rows) == ["expired", "pending"]
        subscription = db.get(Subscription, user.id)
        subscription.status = "active"
        subscription.current_period_end = utcnow() + timedelta(days=1)
        db.commit()
        with pytest.raises(HTTPException) as exc:
            begin_checkout(db, settings, user, "pro", gateway)
        assert exc.value.status_code == 409
