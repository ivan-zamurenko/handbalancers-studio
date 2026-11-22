"""Current provider state wins over webhook order; real DB leases and atomic effects."""

import copy
import importlib
from datetime import UTC, datetime
from typing import ClassVar
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import text
from studio.auth.token_store import TokenCipher
from studio.billing.webhooks import WebhookInbox

from server.tests.integration.billing.test_webhook_inbox import raw_event, signed
from server.tests.integration.database.test_auth_storage import (  # noqa: F401
    USER,
    database_engine,
    storage_db,
)
from server.tests.support.actors import role_session


class Provider:
    prices: ClassVar[dict[str, str]] = {
        "essential": "price_essential",
        "plus": "price_plus",
        "pro": "price_pro",
        "pro-plus": "price_proplus",
    }

    def __init__(self, attempt):
        now = int(datetime.now(UTC).timestamp())
        self.subscription = {
            "id": "sub_synthetic",
            "object": "subscription",
            "livemode": False,
            "customer": "cus_synthetic",
            "status": "active",
            "metadata": {"studio_attempt_id": str(attempt)},
            "items": {
                "data": [
                    {
                        "quantity": 1,
                        "current_period_start": now - 100,
                        "current_period_end": now + 86400,
                        "price": {
                            "id": "price_plus",
                            "currency": "eur",
                            "unit_amount": 4999,
                            "recurring": {"interval": "month", "interval_count": 1},
                        },
                    }
                ]
            },
            "latest_invoice": {"status": "paid"},
            "default_payment_method": {"id": "pm_synthetic", "type": "card"},
        }
        self.checkout = {
            "id": "cs_test_synthetic",
            "object": "checkout.session",
            "livemode": False,
            "mode": "subscription",
            "status": "complete",
            "payment_status": "paid",
            "customer": "cus_synthetic",
            "subscription": "sub_synthetic",
            "client_reference_id": str(attempt),
        }
        self.calls = 0

    def retrieve_checkout(self, identifier):
        return copy.deepcopy(self.checkout)

    def retrieve_subscription(self, identifier):
        self.calls += 1
        return copy.deepcopy(self.subscription)


@pytest.fixture
def sync(storage_db):  # noqa: F811
    api = importlib.import_module("studio.billing.reconciliation")
    attempt = uuid4()
    with storage_db.begin() as c:
        c.execute(
            text(
                "INSERT INTO studio.billing_customers(user_id,provider_customer_id) VALUES (:u,'cus_synthetic')"
            ),
            {"u": USER},
        )
        c.execute(
            text(
                "INSERT INTO studio.checkout_attempts(id,user_id,idempotency_key,plan_code,terms_version,state,expires_at,provider_session_id) VALUES (:i,:u,'sync-key','plus','test-v1','open',now()+interval '2 hours','cs_test_synthetic')"
            ),
            {"i": attempt, "u": USER},
        )
    provider = Provider(attempt)
    tx = lambda: role_session(storage_db, "studio_worker")
    inbox = WebhookInbox(
        tx, SecretStr("whsec_synthetic_test_only"), TokenCipher("test", {"test": b"x" * 32})
    )
    worker = api.Reconciler(tx, provider)

    def enqueue(name="evt_synthetic", kind="checkout.session.completed"):
        data = {
            "object": provider.checkout if kind.startswith("checkout.") else provider.subscription
        }
        raw = raw_event(id=name, type=kind, data=data)
        inbox.accept(raw, signed(raw))

    try:
        yield worker, provider, storage_db, enqueue
    finally:
        with storage_db.begin() as c:
            c.execute(text("DELETE FROM studio_private.webhook_events"))
            c.execute(text("DELETE FROM studio.subscriptions"))
            c.execute(text("DELETE FROM studio.trial_claims"))
            c.execute(text("DELETE FROM studio.checkout_attempts"))
            c.execute(text("DELETE FROM studio.billing_customers"))


def test_out_of_order_no_regression(sync):
    worker, provider, db, enqueue = sync
    enqueue()
    assert worker.run_once()
    provider.subscription["status"] = "canceled"
    enqueue("evt_deleted", "customer.subscription.deleted")
    assert worker.run_once()
    enqueue("evt_old_created", "customer.subscription.created")
    assert worker.run_once()
    with db.connect() as c:
        assert c.execute(text("SELECT status,row_version FROM studio.subscriptions")).one() == (
            "canceled",
            2,
        )
        assert (
            c.scalar(
                text("SELECT count(*) FROM studio_private.webhook_events WHERE state='processed'")
            )
            == 3
        )


def test_customer_owner_verified(sync):
    worker, provider, db, enqueue = sync
    provider.checkout["customer"] = "cus_foreign"
    enqueue()
    assert worker.run_once()
    with db.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM studio.subscriptions")) == 0
        assert c.scalar(text("SELECT state FROM studio_private.webhook_events")) == "pending"


def test_repeated_projection_idempotent(sync):
    worker, _provider, db, enqueue = sync
    enqueue()
    worker.run_once()
    enqueue("evt_duplicate", "customer.subscription.updated")
    worker.run_once()
    with db.connect() as c:
        assert c.scalar(text("SELECT row_version FROM studio.subscriptions")) == 1
        assert c.scalar(text("SELECT state FROM studio.checkout_attempts")) == "completed"


def test_network_outside_long_transaction(sync):
    worker, provider, db, enqueue = sync
    original = provider.retrieve_subscription

    def request(identifier):
        with db.begin() as c:
            c.execute(text("SET LOCAL lock_timeout='100ms'"))
            c.execute(text("SELECT * FROM studio.billing_customers FOR UPDATE"))
        return original(identifier)

    provider.retrieve_subscription = request
    enqueue()
    worker.run_once()
    with db.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM studio.subscriptions")) == 1


def test_crash_retry_durable(sync):
    worker, provider, db, enqueue = sync
    original = provider.retrieve_subscription

    def crash(identifier):
        raise RuntimeError("synthetic crash")

    provider.retrieve_subscription = crash
    enqueue()
    with pytest.raises(RuntimeError):
        worker.run_once()
    with db.begin() as c:
        assert c.scalar(text("SELECT count(*) FROM studio.subscriptions")) == 0
        c.execute(
            text("UPDATE studio_private.webhook_events SET lease_until=now()-interval '1 minute'")
        )
        c.execute(
            text("UPDATE studio.billing_customers SET reconcile_until=now()-interval '1 minute'")
        )
    provider.retrieve_subscription = original
    worker.run_once()
    with db.connect() as c:
        assert c.scalar(text("SELECT row_version FROM studio.subscriptions")) == 1


def test_expired_worker_fenced(sync):
    worker, provider, db, enqueue = sync
    original = provider.retrieve_subscription

    def expired(identifier):
        result = original(identifier)
        with db.begin() as c:
            c.execute(
                text("UPDATE studio.billing_customers SET reconcile_token=:t"), {"t": uuid4()}
            )
        return result

    provider.retrieve_subscription = expired
    enqueue()
    worker.run_once()
    with db.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM studio.subscriptions")) == 0


@pytest.mark.parametrize(
    "change", [{"livemode": True}, {"customer": "cus_foreign"}, {"status": "invented"}]
)
def test_invalid_current_subscription_never_grants(sync, change):
    worker, provider, db, enqueue = sync
    provider.subscription.update(change)
    enqueue()
    worker.run_once()
    with db.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM studio.subscriptions")) == 0


def test_missing_webhook_recovered_from_durable_session(sync):
    worker, _provider, db, _enqueue = sync
    with db.begin() as c:
        c.execute(
            text("UPDATE studio.checkout_attempts SET created_at=now()-interval '10 minutes'")
        )
    cipher = TokenCipher("test", {"test": b"x" * 32})
    assert worker.schedule_pending(cipher) == 1
    assert worker.schedule_pending(cipher) == 0
    worker.run_once()
    with db.connect() as c:
        assert c.scalar(text("SELECT status FROM studio.subscriptions")) == "active"
        assert c.scalar(text("SELECT state FROM studio.checkout_attempts")) == "completed"


def test_pending_unpaid_checkout_never_grants(sync):
    worker, provider, db, enqueue = sync
    provider.checkout.update(status="open", subscription=None, payment_status="unpaid")
    enqueue()
    worker.run_once()
    with db.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM studio.subscriptions")) == 0
        assert c.scalar(text("SELECT state FROM studio_private.webhook_events")) == "processed"
        assert c.scalar(text("SELECT state FROM studio.checkout_attempts")) == "open"


def test_unrelated_invoice_with_null_subscription_is_ignored(sync):
    worker, provider, db, _enqueue = sync
    provider.retrieve_invoice = lambda _: {
        "id": "in_unrelated",
        "livemode": False,
        "customer": "cus_synthetic",
        "parent": {"type": "quote_details", "subscription_details": None},
    }
    inbox = WebhookInbox(
        worker.transaction,
        SecretStr("whsec_synthetic_test_only"),
        TokenCipher("test", {"test": b"x" * 32}),
    )
    raw = raw_event(
        id="evt_unrelated_invoice",
        type="invoice.paid",
        data={"object": {"id": "in_unrelated", "object": "invoice", "livemode": False}},
    )
    inbox.accept(raw, signed(raw))
    assert worker.run_once()
    with db.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM studio.subscriptions")) == 0
        assert c.scalar(text("SELECT state FROM studio_private.webhook_events")) == "processed"


def test_recovery_sweep_does_not_starve_eleventh_checkout(sync):
    from tools import local_stack

    worker, _provider, db, _enqueue = sync
    ids = [uuid4() for _ in range(11)]
    values = ",".join(f"('{identifier}')" for identifier in ids)
    local_stack.execute_local_sql(
        local_stack.verify_container("test"),
        f"\\connect {db.url.database}\nINSERT INTO auth.users(id) VALUES {values};",
    )
    with db.begin() as c:
        for i, user in enumerate(ids):
            c.execute(
                text(
                    "INSERT INTO studio.users(id,auth_user_id,locale,timezone) VALUES(:u,:u,'uk','UTC')"
                ),
                {"u": user},
            )
            c.execute(
                text(
                    "INSERT INTO studio.checkout_attempts(user_id,idempotency_key,plan_code,terms_version,state,expires_at,provider_session_id) VALUES(:u,'poll','plus','test-v1','open',now()+interval '1 hour',:p)"
                ),
                {"u": user, "p": f"cs_test_poll_{i}"},
            )
        c.execute(
            text("UPDATE studio.checkout_attempts SET created_at=now()-interval '10 minutes'")
        )
    cipher = TokenCipher("test", {"test": b"x" * 32})
    assert worker.schedule_pending(cipher) == 10
    with db.begin() as c:
        c.execute(text("UPDATE studio_private.webhook_events SET state='processed'"))
    assert worker.schedule_pending(cipher) == 2


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
def test_stale_subscription_replacement_guard(sync, status):
    worker, _provider, db, enqueue = sync
    with db.begin() as c:
        c.execute(
            text(
                "INSERT INTO studio.subscriptions(user_id,provider_subscription_id,plan_code,status,current_period_start,current_period_end) VALUES (:u,'sub_previous','plus',:s,now()-interval '32 days',now()-interval '1 day')"
            ),
            {"u": USER, "s": status},
        )
    enqueue()
    assert worker.run_once()
    terminal = status in {"canceled", "incomplete_expired"}
    with db.connect() as c:
        assert c.execute(
            text("SELECT provider_subscription_id,row_version FROM studio.subscriptions")
        ).one() == (("sub_synthetic", 2) if terminal else ("sub_previous", 1))
        assert c.scalar(text("SELECT state FROM studio.checkout_attempts")) == (
            "completed" if terminal else "open"
        )
