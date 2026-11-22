"""One account trial; reservation survives network ambiguity and client redirects."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from studio.billing.stripe_gateway import BillingUnavailable

from server.tests.integration.billing import test_checkout_attempts as checkout_support
from server.tests.integration.billing import test_subscription_projection as sync_support
from server.tests.integration.database.test_auth_storage import (  # noqa: F401
    database_engine,
    storage_db,
)

api = checkout_support.api
flow = checkout_support.flow
sync = sync_support.sync
begin = checkout_support.begin


def test_one_account_trial(flow):
    service, provider, db = flow
    captured = []
    original = provider.create_checkout

    def create(**params):
        captured.append(params)
        return original(**params)

    provider.create_checkout = create
    begin(service)
    begin(service)
    assert all(p["trial"] is True for p in captured)
    with db.connect() as c:
        assert c.execute(text("SELECT state FROM studio.trial_claims")).one() == ("reserved",)
        assert c.scalar(text("SELECT count(*) FROM studio.trial_claims")) == 1


def test_parallel_essential_plus_cannot_reserve_twice(api, flow):
    service, _provider, db = flow
    barrier = Barrier(2)

    def call(plan):
        barrier.wait(timeout=5)
        try:
            begin(service, key=plan, plan=plan)
            return "created"
        except api.CheckoutConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(call, ("essential", "plus"))) == ["conflict", "created"]
    with db.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM studio.trial_claims")) == 1


@pytest.mark.parametrize("plan", ["pro", "pro-plus"])
def test_pro_no_trial(flow, plan):
    service, provider, db = flow
    original = provider.create_checkout

    def create(**params):
        assert params["trial"] is False
        return original(**params)

    provider.create_checkout = create
    begin(service, plan=plan)
    with db.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM studio.trial_claims")) == 0


def test_no_trial_from_redirect_or_network_failure(flow):
    service, provider, db = flow
    provider.fail = True
    with pytest.raises(BillingUnavailable):
        begin(service)
    with db.connect() as c:
        row = c.execute(text("SELECT attempt_id,state FROM studio.trial_claims")).one()
    assert (
        service.get(checkout_support.Actor(checkout_support.USER), row.attempt_id)["state"]
        == "creating"
    )
    with db.connect() as c:
        assert c.scalar(text("SELECT state FROM studio.trial_claims")) == "reserved"


def test_confirmed_trial_cannot_be_released_or_deleted(sync):
    worker, provider, db, enqueue = sync
    now = provider.subscription["items"]["data"][0]["current_period_start"]
    provider.subscription.update(status="trialing", trial_start=now, trial_end=now + 7 * 86400)
    provider.checkout["payment_status"] = "no_payment_required"
    with db.begin() as c:
        c.execute(text("UPDATE studio.checkout_attempts SET trial_enabled=true"))
        c.execute(
            text(
                "INSERT INTO studio.trial_claims(user_id,attempt_id,state) SELECT user_id,id,'reserved' FROM studio.checkout_attempts"
            )
        )
    enqueue()
    worker.run_once()
    with db.connect() as c:
        assert c.scalar(text("SELECT state FROM studio.trial_claims")) == "claimed"
    with pytest.raises(IntegrityError), db.begin() as c:
        c.execute(text("UPDATE studio.trial_claims SET state='released'"))


def test_failed_attempt_recovery_releases_only_verified_expiry(sync):
    worker, provider, db, enqueue = sync
    provider.checkout.update(status="expired", subscription=None, payment_status="unpaid")
    with db.begin() as c:
        c.execute(text("UPDATE studio.checkout_attempts SET trial_enabled=true"))
        c.execute(
            text(
                "INSERT INTO studio.trial_claims(user_id,attempt_id,state) SELECT user_id,id,'reserved' FROM studio.checkout_attempts"
            )
        )
    enqueue("evt_expired", "checkout.session.expired")
    worker.run_once()
    with db.connect() as c:
        assert c.scalar(text("SELECT state FROM studio.trial_claims")) == "released"
        assert c.scalar(text("SELECT state FROM studio.checkout_attempts")) == "expired"


def test_claimed_history_prevents_second_trial(flow):
    service, provider, db = flow
    first = begin(service)
    with db.begin() as c:
        c.execute(text("UPDATE studio.trial_claims SET state='claimed'"))
        c.execute(text("UPDATE studio.checkout_attempts SET state='completed'"))
    original = provider.create_checkout

    def create(**params):
        assert params["trial"] is False
        return original(**params)

    provider.create_checkout = create
    second = begin(service, key="next-purchase", plan="plus")
    assert first["id"] != second["id"]
    with db.connect() as c:
        assert c.execute(text("SELECT attempt_id,state FROM studio.trial_claims")).one() == (
            first["id"],
            "claimed",
        )


def test_lost_checkout_response_is_discovered_without_new_payment(sync):
    worker, provider, db, _enqueue = sync
    provider.list_checkouts = lambda customer: [provider.checkout]
    with db.begin() as c:
        c.execute(
            text(
                "UPDATE studio.checkout_attempts SET state='creating',provider_session_id=NULL,created_at=now()-interval '2 minutes'"
            )
        )
    assert worker.discover_pending()
    with db.connect() as c:
        assert (
            c.scalar(text("SELECT provider_session_id FROM studio.checkout_attempts"))
            == provider.checkout["id"]
        )
        assert c.scalar(text("SELECT count(*) FROM studio.subscriptions")) == 0


@pytest.mark.parametrize("expired", [False, True])
def test_missing_remote_checkout_releases_only_after_verified_deadline(sync, expired):
    worker, provider, db, _enqueue = sync
    provider.list_checkouts = lambda customer: []
    with db.begin() as c:
        c.execute(
            text(
                "UPDATE studio.checkout_attempts SET state='creating',provider_session_id=NULL,trial_enabled=true,created_at=now()-interval '3 hours'"
            )
        )
        if expired:
            c.execute(
                text("UPDATE studio.checkout_attempts SET expires_at=now()-interval '1 minute'")
            )
        c.execute(
            text(
                "INSERT INTO studio.trial_claims(user_id,attempt_id,state) SELECT user_id,id,'reserved' FROM studio.checkout_attempts"
            )
        )
    assert worker.discover_pending()
    with db.connect() as c:
        assert c.scalar(text("SELECT state FROM studio.trial_claims")) == (
            "released" if expired else "reserved"
        )
        assert c.scalar(text("SELECT state FROM studio.checkout_attempts")) == (
            "expired" if expired else "creating"
        )


def test_trial_period_cannot_grant_beyond_verified_trial_end(sync):
    worker, provider, db, enqueue = sync
    start = provider.subscription["items"]["data"][0]["current_period_start"]
    provider.subscription.update(status="trialing", trial_start=start, trial_end=start + 7 * 86400)
    provider.subscription["items"]["data"][0]["current_period_end"] = start + 30 * 86400
    provider.checkout["payment_status"] = "no_payment_required"
    with db.begin() as c:
        c.execute(text("UPDATE studio.checkout_attempts SET trial_enabled=true"))
        c.execute(
            text(
                "INSERT INTO studio.trial_claims(user_id,attempt_id,state) SELECT user_id,id,'reserved' FROM studio.checkout_attempts"
            )
        )
    enqueue()
    worker.run_once()
    with db.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM studio.subscriptions")) == 0


def test_customer_timeout_cannot_leave_reserved_trial_forever(flow):
    from studio.billing.reconciliation import Reconciler

    service, provider, db = flow

    def timeout(_):
        raise BillingUnavailable()

    provider.create_customer = timeout
    with pytest.raises(BillingUnavailable):
        begin(service)
    assert provider.keys == []
    with db.begin() as c:
        c.execute(
            text(
                "UPDATE studio.checkout_attempts SET created_at=now()-interval '3 hours',expires_at=now()-interval '1 minute'"
            )
        )
    assert Reconciler(service.transaction, provider).discover_pending()
    with db.connect() as c:
        assert c.scalar(text("SELECT state FROM studio.checkout_attempts")) == "expired"
        assert c.scalar(text("SELECT state FROM studio.trial_claims")) == "released"
        assert c.scalar(text("SELECT count(*) FROM studio.billing_customers")) == 0
    assert provider.keys == []


def test_discovered_open_checkout_restores_pay_link(sync):
    worker, provider, db, _enqueue = sync
    provider.checkout.update(
        status="open",
        subscription=None,
        payment_status="unpaid",
        url="https://checkout.stripe.com/c/pay/cs_test_synthetic",
    )
    provider.list_checkouts = lambda customer: [provider.checkout]
    with db.begin() as c:
        c.execute(
            text(
                "UPDATE studio.checkout_attempts SET state='creating',provider_session_id=NULL,checkout_url=NULL,created_at=now()-interval '2 minutes'"
            )
        )
    assert worker.discover_pending()
    with db.connect() as c:
        assert c.execute(text("SELECT state,checkout_url FROM studio.checkout_attempts")).one() == (
            "open",
            provider.checkout["url"],
        )


def test_discovery_cannot_release_from_stale_missing_customer(sync, monkeypatch):
    from contextlib import contextmanager
    from datetime import timedelta

    from studio.billing import reconciliation

    worker, provider, db, _enqueue = sync
    with db.begin() as c:
        c.execute(text("DELETE FROM studio.billing_customers"))
        c.execute(
            text(
                "UPDATE studio.checkout_attempts SET state='creating',provider_session_id=NULL,trial_enabled=true,created_at=now()-interval '2 minutes'"
            )
        )
        deadline = c.scalar(text("SELECT expires_at FROM studio.checkout_attempts"))
        c.execute(
            text(
                "INSERT INTO studio.trial_claims(user_id,attempt_id,state) SELECT user_id,id,'reserved' FROM studio.checkout_attempts"
            )
        )

    class Clock:
        @staticmethod
        def now(_):
            return deadline + timedelta(seconds=1)

    monkeypatch.setattr(reconciliation, "datetime", Clock)
    original = worker.transaction
    claimed = False

    @contextmanager
    def paused_claim():
        nonlocal claimed
        with original() as s:
            yield s
        if not claimed:
            claimed = True
            # A same-key request commits its customer and creates Checkout while
            # discovery is paused, before expiry. Its response is then lost.
            with db.begin() as c:
                c.execute(
                    text(
                        "INSERT INTO studio.billing_customers(user_id,provider_customer_id) SELECT user_id,:c FROM studio.checkout_attempts"
                    ),
                    {"c": provider.checkout["customer"]},
                )

    worker.transaction = paused_claim
    provider.list_checkouts = lambda customer: [provider.checkout]
    assert worker.discover_pending()
    with db.connect() as c:
        assert c.scalar(text("SELECT state FROM studio.trial_claims")) == "reserved"
        assert c.scalar(text("SELECT state FROM studio.checkout_attempts")) != "expired"


def test_predeadline_empty_listing_cannot_release_after_pause(sync, monkeypatch):
    from datetime import timedelta

    from studio.billing import reconciliation

    worker, provider, db, _enqueue = sync
    with db.begin() as c:
        c.execute(
            text(
                "UPDATE studio.checkout_attempts SET state='creating',provider_session_id=NULL,trial_enabled=true,created_at=now()-interval '2 minutes'"
            )
        )
        deadline = c.scalar(text("SELECT expires_at FROM studio.checkout_attempts"))
        c.execute(
            text(
                "INSERT INTO studio.trial_claims(user_id,attempt_id,state) SELECT user_id,id,'reserved' FROM studio.checkout_attempts"
            )
        )
    current = deadline - timedelta(seconds=1)

    class Clock:
        @staticmethod
        def now(_):
            return current

    monkeypatch.setattr(reconciliation, "datetime", Clock)

    def list_before_deadline(customer):
        nonlocal current
        # Listing completed before expiry; the worker then stalled until after it.
        current = deadline + timedelta(seconds=1)
        return []

    provider.list_checkouts = list_before_deadline
    assert worker.discover_pending()
    with db.connect() as c:
        assert c.scalar(text("SELECT state FROM studio.trial_claims")) == "reserved"
        assert c.scalar(text("SELECT state FROM studio.checkout_attempts")) == "creating"
