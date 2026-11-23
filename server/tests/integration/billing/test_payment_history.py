"""Financial history: real PostgreSQL, real RLS, verified provider boundary fixtures."""

import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from studio.auth.token_store import TokenCipher
from studio.billing.webhooks import WebhookInbox

from server.tests.integration.billing.test_subscription_projection import sync  # noqa: F401
from server.tests.integration.billing.test_webhook_inbox import raw_event, signed
from server.tests.integration.database.test_auth_storage import (  # noqa: F401
    USER,
    database_engine,
    storage_db,
)
from server.tests.support.actors import role_session

PAID_AT = 1795392000


@pytest.fixture
def ledger(sync):  # noqa: F811
    worker, provider, db, _ = sync
    provider.invoice = {
        "id": "in_history",
        "object": "invoice",
        "livemode": False,
        "customer": "cus_synthetic",
        "status": "paid",
        "currency": "eur",
        "amount_paid": 4999,
        "parent": {"subscription_details": {"subscription": "sub_synthetic"}},
        "lines": {
            "has_more": False,
            "data": [
                {
                    "quantity": 1,
                    "currency": "eur",
                    "pricing": {"price_details": {"price": "price_plus"}},
                    "parent": {"subscription_item_details": {"subscription": "sub_synthetic"}},
                }
            ],
        },
    }
    provider.invoice_payment = {
        "id": "inpay_history",
        "object": "invoice_payment",
        "livemode": False,
        "invoice": "in_history",
        "status": "paid",
        "amount_paid": 4999,
        "currency": "eur",
        "payment": {"type": "payment_intent", "payment_intent": "pi_history"},
        "status_transitions": {"paid_at": PAID_AT},
    }
    provider.intent = {
        "id": "pi_history",
        "livemode": False,
        "customer": "cus_synthetic",
        "status": "succeeded",
        "amount_received": 4999,
        "currency": "eur",
        "latest_charge": "ch_history",
    }
    provider.refund = {
        "id": "re_history",
        "object": "refund",
        "status": "succeeded",
        "payment_intent": "pi_history",
        "charge": "ch_history",
        "amount": 999,
        "currency": "eur",
        "created": PAID_AT + 100,
    }
    provider.retrieve_invoice = lambda _: copy.deepcopy(provider.invoice)
    provider.list_invoice_payments = lambda **_: [copy.deepcopy(provider.invoice_payment)]
    provider.retrieve_payment_intent = lambda _: copy.deepcopy(provider.intent)
    provider.retrieve_charge = lambda _: {
        "id": "ch_history",
        "livemode": False,
        "paid": True,
        "status": "succeeded",
        "amount": 4999,
        "currency": "eur",
        "payment_method_details": {"type": "card"},
        "payment_intent": "pi_history",
        "customer": "cus_synthetic",
    }
    provider.retrieve_refund = lambda _: copy.deepcopy(provider.refund)
    inbox = WebhookInbox(
        worker.transaction,
        SecretStr("whsec_synthetic_test_only"),
        TokenCipher("test", {"test": b"x" * 32}),
    )

    def enqueue(event_id="evt_history", refund=False):
        raw = raw_event(
            id=event_id,
            type="refund.updated" if refund else "invoice.paid",
            data={"object": provider.refund if refund else provider.invoice},
        )
        inbox.accept(raw, signed(raw))

    try:
        yield worker, provider, db, enqueue
    finally:
        with db.begin() as c:
            for table in ("payment_refunds", "payments"):
                if c.scalar(text("SELECT to_regclass(:t)"), {"t": "studio." + table}):
                    c.execute(text("DELETE FROM studio." + table))


def rows(db):
    with db.connect() as c:
        return c.execute(text("SELECT * FROM studio.payments")).mappings().all()


def test_confirmed_payment_has_original_facts_and_is_idempotent(ledger):
    worker, _provider, db, enqueue = ledger
    enqueue()
    worker.run_once()
    with db.connect() as c:
        assert c.scalar(text("SELECT to_regclass('studio.payments')")), "Separate payments absent"
    [payment] = rows(db)
    assert payment["user_id"] == USER
    assert payment["plan_code"] == "plus"
    assert payment["amount_minor"] == 4999 and payment["currency"] == "eur"
    assert payment["paid_at"] == datetime.fromtimestamp(PAID_AT, UTC)
    assert payment["livemode"] is False
    assert payment["provider_invoice_id"] == "in_history"
    assert payment["provider_payment_intent_id"] == "pi_history"
    # Exact event replay after completion plus a new event about same invoice.
    enqueue()
    enqueue("evt_history_again")
    while worker.run_once():
        pass
    assert len(rows(db)) == 1
    with db.connect() as c:
        assert c.scalar(text("SELECT status FROM studio.subscriptions")) == "active"


@pytest.mark.parametrize(
    "mutation",
    [
        "foreign_customer",
        "foreign_checkout",
        "foreign_intent",
        "wrong_invoice",
        "wrong_amount",
        "live",
        "unknown_price",
    ],
)
def test_untrusted_binding_never_records_payment(ledger, mutation):
    worker, p, db, enqueue = ledger
    if mutation == "foreign_customer":
        p.invoice["customer"] = "cus_foreign"
    elif mutation == "foreign_checkout":
        p.checkout["client_reference_id"] = str(UUID(int=99))
    elif mutation == "foreign_intent":
        p.intent["customer"] = "cus_foreign"
    elif mutation == "wrong_invoice":
        p.invoice_payment["invoice"] = "in_foreign"
    elif mutation == "wrong_amount":
        p.intent["amount_received"] = 1
    elif mutation == "live":
        p.intent["livemode"] = True
    else:
        p.invoice["lines"]["data"][0]["pricing"]["price_details"]["price"] = "price_foreign"
    enqueue()
    worker.run_once()
    assert rows(db) == []
    with db.connect() as c:
        assert c.scalar(text("SELECT state FROM studio_private.webhook_events")) == "pending"


def test_trial_zero_invoice_is_not_a_cash_payment(ledger):
    worker, p, db, enqueue = ledger
    p.invoice["amount_paid"] = 0
    p.list_invoice_payments = lambda **_: []
    enqueue()
    worker.run_once()
    assert rows(db) == []


def test_history_survives_current_subscription_replacement(ledger):
    worker, p, db, enqueue = ledger
    # Old completed Checkout, newer current subscription; invoice plan is original.
    with db.begin() as c:
        c.execute(text("UPDATE studio.checkout_attempts SET state='completed'"))
        c.execute(
            text("""INSERT INTO studio.subscriptions
(user_id,provider_subscription_id,plan_code,status,current_period_start,current_period_end)
VALUES(:u,'sub_new','pro','active',now(),now()+interval '30 days')"""),
            {"u": USER},
        )
    p.subscription["status"] = "canceled"
    enqueue()
    while worker.run_once():
        pass
    assert rows(db)[0]["plan_code"] == "plus"
    with db.connect() as c:
        assert (
            c.scalar(text("SELECT provider_subscription_id FROM studio.subscriptions")) == "sub_new"
        )
        assert (
            c.scalar(
                text("SELECT state FROM studio_private.webhook_events WHERE event_id='evt_history'")
            )
            == "processed"
        )


def test_refund_before_invoice_recovers_payment_and_preserves_original(ledger):
    worker, _provider, db, enqueue = ledger
    enqueue(refund=True)
    worker.run_once()
    [payment] = rows(db)
    assert payment["amount_minor"] == 4999
    enqueue("evt_refund_duplicate", refund=True)
    enqueue("evt_invoice_later")
    while worker.run_once():
        pass
    with db.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM studio.payment_refunds")) == 1
        assert c.scalar(text("SELECT amount_minor FROM studio.payment_refunds")) == 999
    assert len(rows(db)) == 1


def test_owner_rls_and_no_runtime_mutation(ledger):
    worker, _provider, db, enqueue = ledger
    enqueue(refund=True)
    worker.run_once()
    for table in ("payments", "payment_refunds"):
        with role_session(db, "studio_web", USER) as s:
            assert len(s.execute(text("SELECT * FROM studio." + table)).all()) == 1
        for actor in (UUID(int=99), None):
            with role_session(db, "studio_web", actor) as s:
                assert s.execute(text("SELECT * FROM studio." + table)).all() == []
        for role in ("studio_web", "studio_worker", "anon", "authenticated"):
            for operation in ("UPDATE", "DELETE", "TRUNCATE"):
                with db.connect() as s:
                    assert not s.scalar(
                        text("SELECT has_table_privilege(:r,:t,:p)"),
                        {"r": role, "t": "studio." + table, "p": operation},
                    )
        for role in ("anon", "authenticated"):
            with db.connect() as s:
                assert not s.scalar(
                    text("SELECT has_table_privilege(:r,:t,'SELECT,INSERT')"),
                    {"r": role, "t": "studio." + table},
                )
        with pytest.raises(DBAPIError), db.begin() as c:
            c.execute(text("UPDATE studio." + table + " SET amount_minor=1"))


def test_expired_lease_rolls_back_payment_and_followup(ledger):
    worker, p, db, enqueue = ledger
    original = p.retrieve_payment_intent

    def expire(identifier):
        with db.begin() as c:
            c.execute(
                text(
                    "UPDATE studio_private.webhook_events SET lease_until=now()-interval '1 minute'"
                )
            )
        return original(identifier)

    p.retrieve_payment_intent = expire
    enqueue()
    worker.run_once()
    assert rows(db) == []
    with db.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM studio_private.webhook_events")) == 1


def test_concurrent_events_create_one_payment(ledger):
    worker, _provider, db, enqueue = ledger
    enqueue("evt_parallel_one")
    enqueue("evt_parallel_two")
    with ThreadPoolExecutor(2) as pool:
        assert all(pool.map(lambda _: worker.run_once(), range(2)))
    with db.begin() as c:
        c.execute(
            text("UPDATE studio_private.webhook_events SET next_retry=now() WHERE state='pending'")
        )
    while worker.run_once():
        pass
    assert len(rows(db)) == 1
    with db.connect() as c:
        assert c.execute(
            text("SELECT state FROM studio_private.webhook_events")
        ).scalars().all() == ["processed", "processed"]


def test_refund_failure_restores_balance_even_after_stale_delivery(ledger):
    worker, p, db, enqueue = ledger
    enqueue(refund=True)
    worker.run_once()
    p.refund["status"] = "failed"
    enqueue("evt_refund_failed", refund=True)
    worker.run_once()
    # Incoming payload says succeeded, but provider's current object stays failed.
    old = copy.deepcopy(p.refund)
    old["status"] = "succeeded"
    raw = raw_event(id="evt_stale_refund", type="refund.updated", data={"object": old})
    inbox = WebhookInbox(
        worker.transaction,
        SecretStr("whsec_synthetic_test_only"),
        TokenCipher("test", {"test": b"x" * 32}),
    )
    inbox.accept(raw, signed(raw))
    worker.run_once()
    with db.connect() as c:
        assert c.scalar(text("SELECT status FROM studio.payment_refunds")) == "failed"
    assert rows(db)[0]["amount_minor"] == 4999
    from studio.billing.payments import payment_history
    from studio.shared.context import Actor

    [item] = payment_history(lambda a: role_session(db, "studio_web", a.user_id), Actor(USER))[
        "payments"
    ]
    assert item["status"] == "paid" and item["refunded_minor"] == 0
    assert item["refunds"][0]["status"] == "failed"


def test_refunds_cannot_exceed_payment(ledger):
    worker, p, db, enqueue = ledger
    enqueue(refund=True)
    worker.run_once()
    p.refund.update(id="re_excess", amount=4999)
    enqueue("evt_excess", refund=True)
    worker.run_once()
    with db.connect() as c:
        assert c.scalar(text("SELECT sum(amount_minor) FROM studio.payment_refunds")) == 999
        assert (
            c.scalar(
                text("SELECT state FROM studio_private.webhook_events WHERE event_id='evt_excess'")
            )
            == "pending"
        )


def test_conflicting_financial_fact_is_not_silently_accepted(ledger):
    worker, p, db, enqueue = ledger
    enqueue()
    worker.run_once()
    p.invoice_payment["status_transitions"]["paid_at"] += 1
    enqueue("evt_conflicting")
    worker.run_once()
    assert rows(db)[0]["paid_at"] == datetime.fromtimestamp(PAID_AT, UTC)
    with db.connect() as c:
        assert (
            c.scalar(
                text(
                    "SELECT state FROM studio_private.webhook_events WHERE event_id='evt_conflicting'"
                )
            )
            == "pending"
        )


@pytest.mark.parametrize(
    "fault", ["multiple_invoices", "foreign_charge", "live_charge", "foreign_refund"]
)
def test_refund_binding_and_allocation_fail_closed(ledger, fault):
    worker, p, db, enqueue = ledger
    if fault == "multiple_invoices":
        original = p.list_invoice_payments
        p.list_invoice_payments = lambda **kw: original(**kw) * (2 if "payment_intent" in kw else 1)
    elif fault == "foreign_refund":
        p.refund["payment_intent"] = "pi_foreign"
    else:
        original = p.retrieve_charge
        p.retrieve_charge = lambda i: {
            **original(i),
            **({"livemode": True} if fault == "live_charge" else {"customer": "cus_foreign"}),
        }
    enqueue(refund=True)
    worker.run_once()
    assert rows(db) == []
    with db.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM studio.payment_refunds")) == 0


def test_current_refund_read_happens_after_lease_and_loss_rolls_back(ledger):
    worker, p, db, enqueue = ledger
    original = p.retrieve_refund
    calls = 0

    def lose_lease(identifier):
        nonlocal calls
        calls += 1
        if calls == 2:
            with db.begin() as c:
                assert c.scalar(
                    text("SELECT reconcile_token IS NOT NULL FROM studio.billing_customers")
                )
                c.execute(
                    text(
                        "UPDATE studio.billing_customers SET reconcile_until=now()-interval '1 minute'"
                    )
                )
        return original(identifier)

    p.retrieve_refund = lose_lease
    enqueue(refund=True)
    worker.run_once()
    assert calls == 2 and rows(db) == []
    with db.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM studio.payment_refunds")) == 0


def test_invoice_plan_survives_portal_plan_change(ledger):
    worker, p, db, enqueue = ledger
    enqueue()
    worker.run_once()
    p.subscription["items"]["data"][0]["price"].update(id="price_pro", unit_amount=17999)
    enqueue("evt_old_invoice_after_upgrade")
    worker.run_once()
    assert rows(db)[0]["plan_code"] == "plus"
    with db.connect() as c:
        assert c.scalar(text("SELECT plan_code FROM studio.subscriptions")) == "pro"


def test_concurrent_invoice_and_refund_and_partial_totals(ledger):
    worker, p, db, enqueue = ledger
    enqueue()
    enqueue("evt_parallel_refund", refund=True)
    with ThreadPoolExecutor(2) as pool:
        assert all(pool.map(lambda _: worker.run_once(), range(2)))
    # Lease contention is intentionally retried, never silently dropped.
    with db.begin() as c:
        c.execute(
            text("UPDATE studio_private.webhook_events SET next_retry=now() WHERE state='pending'")
        )
    while worker.run_once():
        pass
    p.refund.update(id="re_second_partial", amount=4000)
    enqueue("evt_second_refund", refund=True)
    worker.run_once()
    from studio.billing.payments import payment_history
    from studio.shared.context import Actor

    summary = payment_history(lambda a: role_session(db, "studio_web", a.user_id), Actor(USER))
    [payment] = summary["payments"]
    assert payment["status"] == "refunded" and payment["refunded_minor"] == 4999
    assert len(payment["refunds"]) == 2 and len(rows(db)) == 1


def test_nested_refunds_are_bounded_but_total_is_complete(ledger):
    worker, _provider, db, enqueue = ledger
    enqueue()
    worker.run_once()
    [payment] = rows(db)
    with db.begin() as c:
        c.execute(
            text("""INSERT INTO studio.payment_refunds
(payment_id,user_id,provider_refund_id,status,amount_minor,currency,created_at)
SELECT :p,:u,'re_bounded_'||i,'succeeded',1,'eur',now() FROM generate_series(1,105) i"""),
            {"p": payment["id"], "u": USER},
        )
    from studio.billing.payments import payment_history
    from studio.shared.context import Actor

    [item] = payment_history(lambda a: role_session(db, "studio_web", a.user_id), Actor(USER))[
        "payments"
    ]
    assert len(item["refunds"]) == 100
    assert item["refunds_has_more"] is True and item["refunded_minor"] == 105


def test_noncard_charge_is_rejected(ledger):
    worker, p, db, enqueue = ledger
    original = p.retrieve_charge
    p.retrieve_charge = lambda i: {**original(i), "payment_method_details": {"type": "sepa_debit"}}
    enqueue()
    worker.run_once()
    assert rows(db) == []


def test_historical_payment_requires_customer_lease(ledger):
    worker, p, db, enqueue = ledger
    with db.begin() as c:
        c.execute(text("UPDATE studio.checkout_attempts SET state='completed'"))
        c.execute(
            text("""INSERT INTO studio.subscriptions
(user_id,provider_subscription_id,plan_code,status,current_period_start,current_period_end)
VALUES(:u,'sub_new','pro','active',now(),now()+interval '30 days')"""),
            {"u": USER},
        )
    original = p.retrieve_subscription
    calls = 0

    def expire(identifier):
        nonlocal calls
        calls += 1
        if calls == 2:
            with db.begin() as c:
                c.execute(
                    text(
                        "UPDATE studio.billing_customers SET reconcile_until=now()-interval '1 minute'"
                    )
                )
        return original(identifier)

    p.retrieve_subscription = expire
    enqueue()
    worker.run_once()
    assert rows(db) == []


def test_payment_conflict_rolls_back_entitlement_change(ledger):
    worker, p, db, enqueue = ledger
    enqueue()
    worker.run_once()
    with db.connect() as c:
        before = c.execute(text("SELECT status,row_version FROM studio.subscriptions")).one()
    p.subscription["status"] = "canceled"
    p.invoice_payment["status_transitions"]["paid_at"] += 1
    enqueue("evt_atomic_conflict")
    worker.run_once()
    with db.connect() as c:
        assert (
            c.execute(text("SELECT status,row_version FROM studio.subscriptions")).one() == before
        )
        assert (
            c.scalar(
                text(
                    "SELECT state FROM studio_private.webhook_events WHERE event_id='evt_atomic_conflict'"
                )
            )
            == "pending"
        )
    assert rows(db)[0]["paid_at"] == datetime.fromtimestamp(PAID_AT, UTC)


def test_refund_race_refetches_status_after_lease(ledger):
    from threading import Event, current_thread

    worker, p, db, enqueue = ledger
    # First establish the original refund.
    enqueue(refund=True)
    worker.run_once()
    read_old, allow_old = Event(), Event()
    original = p.retrieve_refund
    blocked = False

    def delayed(identifier):
        nonlocal blocked
        result = original(identifier)
        if current_thread().name.startswith("older") and not blocked:
            blocked = True
            read_old.set()
            assert allow_old.wait(10)
        return result

    p.retrieve_refund = delayed
    enqueue("evt_refund_race_older", refund=True)
    with ThreadPoolExecutor(1, thread_name_prefix="older") as pool:
        future = pool.submit(worker.run_once)
        assert read_old.wait(10)
        try:
            p.refund["status"] = "failed"
            enqueue("evt_refund_race_newer", refund=True)
            assert worker.run_once()
        finally:
            allow_old.set()
        assert future.result(timeout=10)
    with db.connect() as c:
        assert c.scalar(text("SELECT status FROM studio.payment_refunds")) == "failed"
        assert set(
            c.execute(text("SELECT state FROM studio_private.webhook_events")).scalars()
        ) == {"processed"}


@pytest.mark.parametrize("field", ["price_details", "subscription_item_details"])
def test_nullable_stripe_line_fields_fail_closed_without_crashing_worker(ledger, field):
    worker, p, db, enqueue = ledger
    line = p.invoice["lines"]["data"][0]
    line["pricing" if field == "price_details" else "parent"][field] = None
    enqueue()
    assert worker.run_once()
    assert rows(db) == []
    with db.connect() as c:
        assert c.scalar(text("SELECT state FROM studio_private.webhook_events")) == "pending"
