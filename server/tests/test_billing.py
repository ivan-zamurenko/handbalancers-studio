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
        "status": "complete",
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


@pytest.fixture
def trial_checkout(paid_checkout):
    attempt, checkout = paid_checkout
    attempt.trial_days = 7
    checkout["amount_total"] = 0
    checkout["payment_status"] = "no_payment_required"
    checkout["subscription"].update(
        status="trialing", trial_start=int(time.time()), trial_end=int(time.time()) + 7 * 86400
    )
    checkout["subscription"].pop("current_period_end")
    return attempt, checkout


def test_trial_zero_charge_requires_approved_trial_and_valid_dates(trial_checkout):
    attempt, checkout = trial_checkout
    validate_paid_checkout(attempt, checkout)
    assert period_end(checkout["subscription"]).timestamp() == checkout["subscription"]["trial_end"]
    attempt.trial_days = 0
    with pytest.raises(BillingUnavailable):
        validate_paid_checkout(attempt, checkout)


@pytest.mark.parametrize(
    "change",
    [
        {"amount_total": 4999},
        {"payment_status": "unpaid"},
        {"status": "open"},
        {"client_reference_id": "another-user"},
        {"currency": "usd"},
    ],
)
def test_trial_rejects_mismatched_checkout(trial_checkout, change):
    attempt, checkout = trial_checkout
    with pytest.raises(BillingUnavailable):
        validate_paid_checkout(attempt, checkout | change)


@pytest.mark.parametrize(
    "change",
    [
        {"trial_end": 1},
        {"trial_start": None},
        {"trial_end": int(time.time()) + 8 * 86400},
        {"status": "active"},
    ],
)
def test_trial_rejects_invalid_subscription(trial_checkout, change):
    attempt, checkout = trial_checkout
    checkout["subscription"].update(change)
    with pytest.raises(BillingUnavailable):
        validate_paid_checkout(attempt, checkout)


def test_gateway_requires_card_and_only_adds_trial_when_authorized(
    monkeypatch, settings, paid_checkout
):
    from types import SimpleNamespace

    import stripe

    attempt, _ = paid_checkout
    captured = []
    monkeypatch.setattr(
        stripe.Price,
        "retrieve",
        lambda *a, **k: {
            "active": True,
            "unit_amount": 4999,
            "currency": "eur",
            "recurring": {"interval": "month", "interval_count": 1},
        },
    )

    def create(**kwargs):
        captured.append(kwargs)
        return SimpleNamespace(id="cs_fixture", url="https://checkout.stripe.com/fixture")

    monkeypatch.setattr(stripe.checkout.Session, "create", create)
    for days in (0, 7):
        attempt.trial_days = days
        StripeGateway(settings).create_checkout(attempt)
    assert captured[0]["payment_method_collection"] == "always"
    assert "trial_period_days" not in captured[0]["subscription_data"]
    assert captured[1]["subscription_data"]["trial_period_days"] == 7


@pytest.mark.postgres
def test_successful_trial_is_consumed_once_and_cancellation_is_synced(db_factory, trial_checkout):
    with db_factory() as db:
        attempt, checkout = seed_checkout(db, trial_checkout)
        checkout["subscription"]["cancel_at_period_end"] = True
        gateway = FakeGateway(checkout)
        apply_webhook(db, completion_event(checkout), gateway)
        first_use = db.get(User, attempt.user_id).trial_used_at
        assert first_use is not None
        assert db.get(Subscription, attempt.user_id).status == "trialing"
        assert db.get(Subscription, attempt.user_id).cancel_at_period_end is True
        apply_webhook(db, completion_event(checkout), gateway)
        assert db.get(User, attempt.user_id).trial_used_at == first_use


@pytest.mark.postgres
@pytest.mark.parametrize(
    "plan,used,days",
    [
        ("essential", False, 7),
        ("plus", False, 7),
        ("pro", False, 0),
        ("pro_plus", False, 0),
        ("plus", True, 0),
    ],
)
def test_trial_eligibility_is_server_owned(db_factory, settings, plan, used, days):
    from pydantic import SecretStr

    settings.stripe_secret_key = SecretStr("test-fixture-only")
    settings.stripe_webhook_secret = SecretStr("test-fixture-only")
    for name in ("essential", "plus", "pro", "pro_plus"):
        setattr(settings, "stripe_price_" + name, "price_" + name)
    with db_factory() as db:
        user = User(name="Fixture", trial_used_at=utcnow() if used else None)
        db.add(user)
        db.commit()
        begin_checkout(db, settings, user, plan, FakeGateway({}))
        attempt = db.scalar(select(CheckoutAttempt).where(CheckoutAttempt.user_id == user.id))
        assert attempt.trial_days == days
        assert user.trial_used_at is None if not used else user.trial_used_at is not None


def test_cancel_renewal_preserves_period(monkeypatch, settings):
    import stripe

    def modify(sub_id, **kwargs):
        assert sub_id == "sub_fixture"
        assert kwargs["cancel_at_period_end"] is True
        return {"id": sub_id, "status": "trialing", "cancel_at_period_end": True}

    monkeypatch.setattr(stripe.Subscription, "modify", modify)
    assert StripeGateway(settings).cancel_at_period_end("sub_fixture")["status"] == "trialing"


@pytest.mark.parametrize("plan", ["pro", "pro_plus"])
def test_free_checkout_is_rejected_for_mentor_plans(trial_checkout, plan):
    attempt, checkout = trial_checkout
    attempt.plan_id = plan
    with pytest.raises(BillingUnavailable):
        validate_paid_checkout(attempt, checkout)


@pytest.mark.postgres
def test_switch_after_lost_response_recovers_same_attempt_before_expiring(db_factory, settings):
    from pydantic import SecretStr

    settings.stripe_secret_key = SecretStr("test-fixture-only")
    settings.stripe_webhook_secret = SecretStr("test-fixture-only")
    for plan in ("essential", "plus", "pro", "pro_plus"):
        setattr(settings, "stripe_price_" + plan, "price_" + plan)

    class LostResponseGateway(FakeGateway):
        def create_checkout(self, attempt):
            result = super().create_checkout(attempt)
            if len(self.created) == 1:
                raise BillingUnavailable("Simulated lost response")
            return result

    with db_factory() as db:
        user = User(name="Retry")
        db.add(user)
        db.commit()
        gateway = LostResponseGateway({})
        with pytest.raises(HTTPException) as error:
            begin_checkout(db, settings, user, "essential", gateway)
        assert error.value.status_code == 503
        db.rollback()
        result = begin_checkout(db, settings, user, "plus", gateway)
        assert result.startswith("https://checkout.stripe.com/")
        assert gateway.created[0] == gateway.created[1]
        assert gateway.created[2] != gateway.created[0]
        assert gateway.expired == [f"cs_{gateway.created[0]}"]
        assert db.scalar(select(func.count()).select_from(Subscription)) == 1


@pytest.mark.postgres
def test_unknown_checkout_older_than_idempotency_window_is_not_recreated(db_factory, settings):
    from pydantic import SecretStr

    settings.stripe_secret_key = SecretStr("test-fixture-only")
    settings.stripe_webhook_secret = SecretStr("test-fixture-only")
    for plan in ("essential", "plus", "pro", "pro_plus"):
        setattr(settings, "stripe_price_" + plan, "price_" + plan)
    with db_factory() as db:
        user = User(name="Old checkout")
        db.add(user)
        db.flush()
        db.add(
            CheckoutAttempt(
                user_id=user.id,
                plan_id="essential",
                amount_cents=1999,
                currency="EUR",
                stripe_price_id="price_essential",
                status="pending",
                created_at=utcnow() - timedelta(hours=25),
            )
        )
        db.commit()
        gateway = FakeGateway({})
        with pytest.raises(HTTPException) as error:
            begin_checkout(db, settings, user, "plus", gateway)
        assert error.value.status_code == 409
        assert gateway.created == []
        assert gateway.expired == []


def test_demo_membership_does_not_grant_production_access():
    from studio.billing import active_subscription

    subscription = Subscription(
        status="active", is_demo=True, current_period_end=utcnow() + timedelta(days=10)
    )
    assert active_subscription(subscription)
    assert not active_subscription(subscription, allow_demo=False)
