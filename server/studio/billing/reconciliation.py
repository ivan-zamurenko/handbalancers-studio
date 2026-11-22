"""Lease-fenced reconciliation: provider reads never hold a database transaction."""

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from studio.auth.token_store import TokenCipher
from studio.billing.checkout import BillingTransaction
from studio.billing.stripe_gateway import AMOUNTS, BillingUnavailable
from studio.billing.trials import confirm, release


class BindingMismatch(ValueError):
    pass


def require(condition: bool) -> None:
    if not condition:
        raise BindingMismatch()


def subscription_snapshot(sub: dict[str, Any], prices: dict[str, str]) -> dict[str, Any]:
    require(sub.get("livemode") is False)
    items = sub.get("items", {}).get("data", [])
    require(len(items) == 1 and items[0].get("quantity") == 1)
    item = items[0]
    price = item.get("price", {})
    plan = next((p for p, i in prices.items() if i == price.get("id")), None)
    if plan is None:
        raise BindingMismatch()
    recurring = price.get("recurring") or {}
    require(
        price.get("currency") == "eur"
        and price.get("unit_amount") == AMOUNTS[plan]
        and recurring.get("interval") == "month"
        and recurring.get("interval_count") == 1
    )
    status = sub.get("status")
    require(
        status
        in {
            "active",
            "trialing",
            "past_due",
            "unpaid",
            "canceled",
            "paused",
            "incomplete",
            "incomplete_expired",
        }
    )
    if status == "active":
        require((sub.get("latest_invoice") or {}).get("status") == "paid")
    if status == "trialing":
        require(
            plan in {"essential", "plus"}
            and (sub.get("default_payment_method") or {}).get("type") == "card"
        )
        require(0 < sub.get("trial_end", 0) - sub.get("trial_start", 0) <= 7 * 86400)
    start, end = item.get("current_period_start"), item.get("current_period_end")
    require(type(start) is int and type(end) is int and 0 < start < end < 253402300800)
    if status == "trialing":
        require(end <= sub["trial_end"])
    return {
        "subscription_id": sub["id"],
        "plan_code": plan,
        "status": status,
        "start": datetime.fromtimestamp(start, UTC),
        "end": datetime.fromtimestamp(end, UTC),
    }


class Reconciler:
    def __init__(self, transaction: BillingTransaction, gateway: Any):
        self.transaction = transaction
        self.gateway = gateway

    def discover_pending(self) -> bool:
        """Recover one lost create response; complete listing required, five attempts max.

        A missing session releases the reservation only after the original fixed
        Checkout expiry, when Stripe cannot accept that original create anymore.
        Missing/ambiguous/truncated provider results keep the reservation closed.
        """
        with self.transaction() as s:
            row = (
                s.execute(
                    text("""SELECT a.*,c.provider_customer_id
FROM studio.checkout_attempts a LEFT JOIN studio.billing_customers c ON c.user_id=a.user_id
WHERE a.state='creating' AND a.provider_session_id IS NULL AND a.discovery_attempts<5
AND a.created_at<now()-interval '1 minute' AND a.next_discovery<=now()
ORDER BY a.created_at,a.id FOR UPDATE OF a SKIP LOCKED LIMIT 1""")
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                return False
            attempt = dict(row)
            s.execute(
                text(
                    "UPDATE studio.checkout_attempts SET discovery_attempts=discovery_attempts+1,next_discovery=now()+interval '30 minutes' WHERE id=:i"
                ),
                {"i": attempt["id"]},
            )
        try:
            customer = attempt["provider_customer_id"]
            if customer is None and attempt["expires_at"] > datetime.now(UTC):
                # Same durable customer key; Checkout cannot be sent before its
                # local customer binding commits. No card/payment is created here.
                customer = self.gateway.create_customer(attempt["user_id"])
                with self.transaction() as s:
                    s.execute(
                        text(
                            "INSERT INTO studio.billing_customers(user_id,provider_customer_id) VALUES(:u,:c) ON CONFLICT(user_id) DO NOTHING"
                        ),
                        {"u": attempt["user_id"], "c": customer},
                    )
                    require(
                        s.scalar(
                            text(
                                "SELECT provider_customer_id FROM studio.billing_customers WHERE user_id=:u"
                            ),
                            {"u": attempt["user_id"]},
                        )
                        == customer
                    )
            # An empty listing is conclusive only if it STARTED after expiry.
            # A listing before expiry may race with an original create request.
            discovery_started = datetime.now(UTC)
            sessions = self.gateway.list_checkouts(customer) if customer is not None else []
            matches = [
                item for item in sessions if item.get("client_reference_id") == str(attempt["id"])
            ]
            require(len(matches) <= 1)
            if matches:
                checkout = matches[0]
                require(
                    checkout.get("livemode") is False
                    and checkout.get("mode") == "subscription"
                    and checkout.get("customer") == customer
                    and isinstance(checkout.get("id"), str)
                )
                if checkout.get("status") == "open":
                    require(
                        isinstance(checkout.get("url"), str)
                        and checkout["url"].startswith("https://checkout.stripe.com/")
                    )
            with self.transaction() as s:
                row = (
                    s.execute(
                        text(
                            "SELECT * FROM studio.checkout_attempts WHERE id=:i AND state='creating' AND provider_session_id IS NULL FOR UPDATE"
                        ),
                        {"i": attempt["id"]},
                    )
                    .mappings()
                    .one_or_none()
                )
                if row is None:
                    return True
                if row["discovery_attempts"] != attempt["discovery_attempts"] + 1:
                    return True  # A newer discovery owns the decision now.
                if matches:
                    s.execute(
                        text(
                            "UPDATE studio.checkout_attempts SET provider_session_id=:p,state=:s,checkout_url=:url WHERE id=:i"
                        ),
                        {
                            "p": matches[0]["id"],
                            "i": attempt["id"],
                            "s": "open" if matches[0].get("status") == "open" else "pending",
                            "url": matches[0].get("url")
                            if matches[0].get("status") == "open"
                            else None,
                        },
                    )
                elif attempt["expires_at"] <= discovery_started:
                    # Re-read AFTER the deadline: an initial missing binding can
                    # become stale while the worker is paused. A Checkout is sent
                    # only after its customer binding commits. No later create can
                    # succeed with the original, now-expired expires_at.
                    current_customer = s.scalar(
                        text(
                            "SELECT provider_customer_id FROM studio.billing_customers WHERE user_id=:u"
                        ),
                        {"u": attempt["user_id"]},
                    )
                    if current_customer != customer:
                        return True
                    s.execute(
                        text(
                            "UPDATE studio.checkout_attempts SET state='expired',checkout_url=NULL WHERE id=:i"
                        ),
                        {"i": attempt["id"]},
                    )
                    release(s, attempt["id"])
        except (BillingUnavailable, BindingMismatch, SQLAlchemyError):
            pass  # Keep the durable reservation; next discovery is bounded above.
        return True

    def schedule_pending(self, cipher: TokenCipher) -> int:
        """At most ten known Checkout sessions per tick, once per five-minute bucket.

        Failed queues require operator attention; this sweep cannot reset their
        retry budget. Unknown provider outcomes without a session ID remain closed.
        """
        bucket = int(datetime.now(UTC).timestamp()) // 300
        count = 0
        with self.transaction() as session:
            rows = (
                session.execute(
                    text("""SELECT a.id,a.provider_session_id
FROM studio.checkout_attempts a
WHERE a.state IN ('creating','open','pending','needs_reconcile')
AND a.provider_session_id IS NOT NULL AND a.created_at<now()-interval '1 minute'
AND NOT EXISTS (SELECT 1 FROM studio_private.webhook_events e
 WHERE e.object_id=a.provider_session_id AND e.state IN ('pending','processing','failed'))
AND NOT EXISTS (SELECT 1 FROM studio_private.webhook_events e
 WHERE e.event_id='reconcile:'||a.id::text||':'||:bucket)
ORDER BY a.created_at,a.id LIMIT 10"""),
                    {"bucket": str(bucket)},
                )
                .mappings()
                .all()
            )
            for row in rows:
                event_id = f"reconcile:{row['id']}:{bucket}"
                payload = cipher.encrypt(
                    json.dumps({"source": "local_reconcile", "attempt_id": str(row["id"])}),
                    ("stripe-event", event_id),
                )
                added = session.scalar(
                    text("""INSERT INTO studio_private.webhook_events
(event_id,event_type,object_id,encrypted_payload) VALUES(:e,'checkout.session.reconcile',:o,:p)
ON CONFLICT(event_id) DO NOTHING RETURNING event_id"""),
                    {"e": event_id, "o": row["provider_session_id"], "p": payload},
                )
                count += added is not None
        return count

    def _claim(self) -> dict[str, Any] | None:
        with self.transaction() as s:
            s.execute(
                text(
                    "UPDATE studio_private.webhook_events SET state='failed',last_error='retry_exhausted' WHERE attempts>=5 AND (state='pending' OR (state='processing' AND lease_until<now()))"
                )
            )
            row = (
                s.execute(
                    text(
                        "SELECT * FROM studio_private.webhook_events WHERE attempts<5 AND ((state='pending' AND next_retry<=now()) OR (state='processing' AND lease_until<now())) ORDER BY received_at,event_id FOR UPDATE SKIP LOCKED LIMIT 1"
                    )
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                return None
            token = uuid4()
            s.execute(
                text(
                    "UPDATE studio_private.webhook_events SET state='processing',attempts=attempts+1,lease_token=:t,lease_until=now()+interval '90 seconds' WHERE event_id=:e"
                ),
                {"t": token, "e": row["event_id"]},
            )
            return {**row, "lease_token": token}

    def run_once(self) -> bool:
        event = self._claim()
        if event is None:
            return False
        try:
            self._reconcile(event)
        except (
            BillingUnavailable,
            BindingMismatch,
            SQLAlchemyError,
            KeyError,
            TypeError,
            ValueError,
        ):
            with self.transaction() as s:
                if event.get("customer_token"):
                    s.execute(
                        text(
                            "UPDATE studio.billing_customers SET reconcile_token=NULL,reconcile_until=NULL WHERE user_id=:u AND reconcile_token=:t"
                        ),
                        {"u": event["owner"], "t": event["customer_token"]},
                    )
                s.execute(
                    text(
                        "UPDATE studio_private.webhook_events SET state=CASE WHEN attempts>=5 THEN 'failed' ELSE 'pending' END,next_retry=now()+interval '30 seconds',lease_token=NULL,lease_until=NULL,last_error='reconcile_unavailable' WHERE event_id=:e AND lease_token=:t"
                    ),
                    {"e": event["event_id"], "t": event["lease_token"]},
                )
        return True

    def _reconcile(self, event: dict[str, Any]) -> None:
        checkout = None
        kind = event["event_type"]
        if kind.startswith("checkout.session."):
            checkout = self.gateway.retrieve_checkout(event["object_id"])
            require(checkout.get("id") == event["object_id"] and checkout.get("livemode") is False)
            customer = checkout.get("customer")
            subscription_id = checkout.get("subscription")
            if checkout.get("status") == "open":
                with self.transaction() as s:
                    self._finish(s, event)
                return
            if checkout.get("status") == "expired":
                self._expire(event, checkout)
                return
        elif kind.startswith("invoice."):
            invoice = self.gateway.retrieve_invoice(event["object_id"])
            require(invoice.get("livemode") is False)
            customer = invoice.get("customer")
            details = (invoice.get("parent") or {}).get("subscription_details")
            if not details:
                with self.transaction() as s:
                    self._finish(s, event)
                return
            subscription_id = details.get("subscription")
        else:
            initial = self.gateway.retrieve_subscription(event["object_id"])
            require(initial.get("livemode") is False and initial.get("id") == event["object_id"])
            customer = initial.get("customer")
            subscription_id = initial.get("id")
        require(isinstance(customer, str) and isinstance(subscription_id, str))
        token = uuid4()
        with self.transaction() as s:
            owner = s.execute(
                text(
                    "UPDATE studio.billing_customers SET reconcile_token=:t,reconcile_until=now()+interval '60 seconds' WHERE provider_customer_id=:c AND (reconcile_until IS NULL OR reconcile_until<now()) RETURNING user_id"
                ),
                {"t": token, "c": customer},
            ).scalar_one_or_none()
            if owner is None:
                raise BindingMismatch()
            current = (
                s.execute(text("SELECT * FROM studio.subscriptions WHERE user_id=:u"), {"u": owner})
                .mappings()
                .one_or_none()
            )
        event["customer_token"] = token
        event["owner"] = owner
        # Re-fetch AFTER acquiring the durable customer lease. A stale initial read
        # or an older event must never overwrite a later current-provider result.
        sub = self.gateway.retrieve_subscription(subscription_id)
        require(sub.get("id") == subscription_id and sub.get("customer") == customer)
        snapshot = subscription_snapshot(sub, self.gateway.prices)
        attempt_id = None
        if current is None or current["provider_subscription_id"] != subscription_id:
            reference = (
                checkout.get("client_reference_id")
                if checkout
                else (sub.get("metadata") or {}).get("studio_attempt_id")
            )
            attempt_id = UUID(str(reference))
            with self.transaction() as s:
                attempt = (
                    s.execute(
                        text("SELECT * FROM studio.checkout_attempts WHERE id=:i AND user_id=:u"),
                        {"i": attempt_id, "u": owner},
                    )
                    .mappings()
                    .one_or_none()
                )
            if attempt is None:
                raise BindingMismatch()
            # Terminal old attempts cannot displace a subsequent subscription.
            require(attempt["state"] in {"creating", "open", "pending", "needs_reconcile"})
            if checkout is None:
                require(isinstance(attempt["provider_session_id"], str))
                checkout = self.gateway.retrieve_checkout(attempt["provider_session_id"])
            require(
                checkout.get("livemode") is False
                and checkout.get("mode") == "subscription"
                and checkout.get("status") == "complete"
                and checkout.get("payment_status") in {"paid", "no_payment_required"}
                and checkout.get("customer") == customer
                and checkout.get("subscription") == subscription_id
                and checkout.get("client_reference_id") == str(attempt_id)
                and attempt["provider_session_id"] in {None, checkout.get("id")}
                and attempt["plan_code"] == snapshot["plan_code"]
            )
            if current is not None:
                # A stale period end is not proof Stripe stopped billing this subscription.
                require(current["status"] in {"canceled", "incomplete_expired"})
        with self.transaction() as s:
            require(
                s.scalar(
                    text(
                        "SELECT 1 FROM studio.billing_customers WHERE user_id=:u AND reconcile_token=:t AND reconcile_until>now() FOR UPDATE"
                    ),
                    {"u": owner, "t": token},
                )
                == 1
            )
            require(
                s.scalar(
                    text(
                        "SELECT 1 FROM studio_private.webhook_events WHERE event_id=:e AND lease_token=:t AND lease_until>now() FOR UPDATE"
                    ),
                    {"e": event["event_id"], "t": event["lease_token"]},
                )
                == 1
            )
            s.execute(
                text("""INSERT INTO studio.subscriptions(user_id,provider_subscription_id,plan_code,status,current_period_start,current_period_end)
VALUES (:u,:subscription_id,:plan_code,:status,:start,:end)
ON CONFLICT(user_id) DO UPDATE SET provider_subscription_id=EXCLUDED.provider_subscription_id,plan_code=EXCLUDED.plan_code,status=EXCLUDED.status,current_period_start=EXCLUDED.current_period_start,current_period_end=EXCLUDED.current_period_end,row_version=studio.subscriptions.row_version+1
WHERE (studio.subscriptions.provider_subscription_id,studio.subscriptions.plan_code,studio.subscriptions.status,studio.subscriptions.current_period_start,studio.subscriptions.current_period_end) IS DISTINCT FROM (EXCLUDED.provider_subscription_id,EXCLUDED.plan_code,EXCLUDED.status,EXCLUDED.current_period_start,EXCLUDED.current_period_end)"""),
                {"u": owner, **snapshot},
            )
            if attempt_id is not None:
                confirm(s, owner, attempt, sub)
                assert checkout is not None
                s.execute(
                    text(
                        "UPDATE studio.checkout_attempts SET state='completed',provider_session_id=:p,checkout_url=NULL WHERE id=:i AND user_id=:u"
                    ),
                    {"p": checkout["id"], "i": attempt_id, "u": owner},
                )
            self._finish(s, event)
            s.execute(
                text(
                    "UPDATE studio.billing_customers SET reconcile_token=NULL,reconcile_until=NULL WHERE user_id=:u AND reconcile_token=:t"
                ),
                {"u": owner, "t": token},
            )

    @staticmethod
    def _finish(s, event) -> None:
        s.execute(
            text(
                "UPDATE studio_private.webhook_events SET state='processed',lease_token=NULL,lease_until=NULL,last_error=NULL WHERE event_id=:e AND lease_token=:t"
            ),
            {"e": event["event_id"], "t": event["lease_token"]},
        )

    def _expire(self, event, checkout) -> None:
        require(checkout.get("mode") == "subscription" and checkout.get("subscription") is None)
        reference = UUID(str(checkout.get("client_reference_id")))
        with self.transaction() as s:
            row = s.execute(
                text(
                    "SELECT a.id,a.provider_session_id FROM studio.checkout_attempts a LEFT JOIN studio.billing_customers c ON c.user_id=a.user_id WHERE a.id=:i AND c.provider_customer_id=:c FOR UPDATE OF a"
                ),
                {"i": reference, "c": checkout.get("customer")},
            ).one_or_none()
            require(row is not None and row.provider_session_id in {None, checkout["id"]})
            s.execute(
                text(
                    "UPDATE studio.checkout_attempts SET state='expired',checkout_url=NULL WHERE id=:i AND state IN ('creating','open','pending','needs_reconcile')"
                ),
                {"i": reference},
            )
            release(s, reference)
            self._finish(s, event)
