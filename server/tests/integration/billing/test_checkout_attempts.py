"""Durable Checkout on real PostgreSQL; provider fake tests only the network contract."""

import importlib
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import text
from studio.shared.context import Actor

from server.tests.integration.database.test_auth_storage import (  # noqa: F401
    USER,
    database_engine,
    storage_db,
)
from server.tests.support.actors import role_session


class Provider:
    def __init__(self):
        self.keys = []
        self.fail = False

    def create_customer(self, user_id):
        return "cus_synthetic_checkout"

    def create_checkout(self, **params):
        self.keys.append(params["attempt_id"])
        if self.fail:
            from studio.billing.stripe_gateway import BillingUnavailable

            raise BillingUnavailable()
        return {
            "id": f"cs_test_{params['attempt_id'].hex}",
            "url": "https://checkout.stripe.com/c/pay/cs_test_synthetic",
            "status": "open",
        }


@pytest.fixture
def api():
    return importlib.import_module("studio.billing.checkout")


@pytest.fixture
def flow(api, storage_db):  # noqa: F811
    with storage_db.begin() as c:
        c.execute(
            text("UPDATE studio.users SET first_name='Synthetic',last_name='Tester' WHERE id=:u"),
            {"u": USER},
        )
        c.execute(
            text(
                "INSERT INTO studio.onboarding_profiles (user_id,goal_codes,self_reported_level,session_minutes,weekdays) VALUES (:u,ARRAY['fitness'],1,30,ARRAY[1]::smallint[])"
            ),
            {"u": USER},
        )
    provider = Provider()
    service = api.CheckoutService(
        transaction=lambda: role_session(storage_db, "studio_worker"),
        web_transaction=lambda actor: role_session(storage_db, "studio_web", actor.user_id),
        gateway=provider,
        origin="http://127.0.0.1:8765",
    )
    try:
        yield service, provider, storage_db
    finally:
        with storage_db.begin() as c:
            c.execute(text("DELETE FROM studio.trial_claims"))
            c.execute(text("DELETE FROM studio.checkout_attempts"))
            c.execute(text("DELETE FROM studio.billing_customers"))
            c.execute(text("DELETE FROM studio.onboarding_profiles"))


def begin(service, key="test-key-1", plan="essential", actor=None):
    return service.begin(actor or Actor(USER), plan_code=plan, terms_version="test-v1", key=key)


def test_parallel_checkout_one_active(api, flow):
    service, provider, db = flow
    barrier = Barrier(2)

    def call(key):
        barrier.wait(timeout=5)
        return begin(service, key=key)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(call, ("key-one", "key-one")))
    assert results[0]["id"] == results[1]["id"]
    assert len(set(provider.keys)) == 1
    with db.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM studio.checkout_attempts")) == 1


def test_timeout_retry_original_key(api, flow):
    from studio.billing.stripe_gateway import BillingUnavailable

    service, provider, db = flow
    provider.fail = True
    with pytest.raises(BillingUnavailable):
        begin(service)
    with db.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM studio.checkout_attempts")) == 1
    provider.fail = False
    retried = begin(service)
    assert provider.keys[0] == provider.keys[1] == retried["id"]
    with pytest.raises(api.CheckoutConflict):
        begin(service, plan="plus")


def test_profile_complete_required(api, flow):
    service, provider, db = flow
    with db.begin() as c:
        c.execute(text("DELETE FROM studio.onboarding_profiles"))
    with pytest.raises(api.CheckoutForbidden):
        begin(service)
    assert provider.keys == []


def test_redirect_not_entitlement_and_foreign_hidden(api, flow):
    service, _provider, db = flow
    result = begin(service)
    assert service.get(Actor(USER), result["id"])["state"] == "open"
    with pytest.raises(api.CheckoutNotFound):
        service.get(Actor(uuid4()), result["id"])
    with db.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM studio.subscriptions")) == 0
    with role_session(db, "studio_web", USER) as s:
        assert s.scalar(text("SELECT count(*) FROM studio.checkout_attempts")) == 1
    with role_session(db, "studio_web", uuid4()) as s:
        assert s.scalar(text("SELECT count(*) FROM studio.checkout_attempts")) == 0


def test_network_outside_transaction_and_intent_committed(api, flow):
    service, provider, db = flow
    original = provider.create_checkout

    def network(**params):
        with db.begin() as c:
            c.execute(text("SET LOCAL lock_timeout='100ms'"))
            assert (
                c.scalar(
                    text("SELECT id FROM studio.checkout_attempts WHERE id=:i FOR UPDATE"),
                    {"i": params["attempt_id"]},
                )
                == params["attempt_id"]
            )
        return original(**params)

    provider.create_checkout = network
    begin(service)


def test_no_new_key_after_ambiguous_expiry(api, flow):
    from studio.billing.stripe_gateway import BillingUnavailable

    service, provider, db = flow
    provider.fail = True
    with pytest.raises(BillingUnavailable):
        begin(service)
    with db.begin() as c:
        c.execute(
            text("UPDATE studio.checkout_attempts SET expires_at=:e"),
            {"e": datetime.now(UTC) + timedelta(minutes=10)},
        )
    provider.fail = False
    with pytest.raises(api.CheckoutConflict):
        begin(service, key="new-key")
    assert len(provider.keys) == 1


@pytest.mark.parametrize(
    "kwargs", [{"terms_version": "fake"}, {"plan_code": "fake"}, {"key": ""}, {"key": "x" * 129}]
)
def test_bad_input_cannot_start(api, flow, kwargs):
    service, provider, _db = flow
    params = {"plan_code": "essential", "terms_version": "test-v1", "key": "okay", **kwargs}
    with pytest.raises(api.CheckoutForbidden):
        service.begin(Actor(USER), **params)
    assert not provider.keys


def test_different_key_cannot_silently_alias_existing_attempt(api, flow):
    service, _provider, _db = flow
    first = begin(service, key="original-key")
    with pytest.raises(api.CheckoutConflict):
        begin(service, key="different-key")
    assert begin(service, key="original-key")["id"] == first["id"]


def test_parallel_distinct_keys_one_success_one_conflict(api, flow):
    service, provider, db = flow
    barrier = Barrier(2)

    def call(key):
        barrier.wait(timeout=5)
        try:
            begin(service, key=key)
            return "created"
        except api.CheckoutConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(call, ("one", "two"))) == ["conflict", "created"]
    assert len(set(provider.keys)) == 1
    with db.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM studio.checkout_attempts")) == 1


@pytest.mark.parametrize(
    "status",
    [
        "active",
        "trialing",
        "past_due",
        "unpaid",
        "paused",
        "incomplete",
        "canceled",
        "incomplete_expired",
    ],
)
def test_stale_subscription_new_purchase_guard(api, flow, status):
    service, provider, db = flow
    first = begin(service, plan="pro")
    with db.begin() as c:
        c.execute(
            text("UPDATE studio.checkout_attempts SET state='completed' WHERE id=:i"),
            {"i": first["id"]},
        )
        c.execute(
            text(
                "INSERT INTO studio.subscriptions(user_id,provider_subscription_id,plan_code,status,current_period_start,current_period_end) VALUES (:u,'sub_existing','plus',:s,now()-interval '32 days',now()-interval '1 day')"
            ),
            {"u": USER, "s": status},
        )
    try:
        # A repeated owned command remains a replay, never a new Stripe call.
        assert begin(service, plan="pro")["id"] == first["id"]
        assert len(provider.keys) == 1
        if status in {"canceled", "incomplete_expired"}:
            assert begin(service, key="new-purchase", plan="pro")["id"] != first["id"]
        else:
            with pytest.raises(api.CheckoutConflict):
                begin(service, key="new-purchase", plan="pro")
            assert len(provider.keys) == 1
            with db.connect() as c:
                assert c.scalar(text("SELECT count(*) FROM studio.checkout_attempts")) == 1
    finally:
        with db.begin() as c:
            c.execute(text("DELETE FROM studio.subscriptions WHERE user_id=:u"), {"u": USER})
