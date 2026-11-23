"""Verified, append-only financial facts; no card data or entitlement decisions."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text

from studio.billing.reconciliation import require


def timestamp(value: Any) -> datetime:
    require(type(value) is int and 0 < value < 253402300800)
    return datetime.fromtimestamp(value, UTC)


def positive(value: Any) -> int:
    require(type(value) is int and 0 < value < 2**63)
    return value


class PaymentHistory:
    def __init__(self, transaction, gateway):
        self.transaction = transaction
        self.gateway = gateway

    def prepare(self, invoice: dict) -> dict | None:
        """All provider calls precede the final transaction. Scope: single-card invoice."""
        require(invoice.get("livemode") is False and invoice.get("status") == "paid")
        if invoice.get("amount_paid") == 0:
            return None  # Free trial/credits are not money collected.
        amount = positive(invoice.get("amount_paid"))
        customer = invoice.get("customer")
        sub_id = invoice["parent"]["subscription_details"]["subscription"]
        require(isinstance(customer, str) and isinstance(sub_id, str))
        sub = self.gateway.retrieve_subscription(sub_id)
        require(
            sub.get("id") == sub_id
            and sub.get("customer") == customer
            and sub.get("livemode") is False
        )
        attempt_id = UUID(str((sub.get("metadata") or {}).get("studio_attempt_id")))
        with self.transaction() as s:
            attempt = (
                s.execute(
                    text("""
SELECT a.*,c.provider_customer_id FROM studio.checkout_attempts a
JOIN studio.billing_customers c ON c.user_id=a.user_id
WHERE a.id=:a AND c.provider_customer_id=:c
"""),
                    {"a": attempt_id, "c": customer},
                )
                .mappings()
                .one_or_none()
            )
        require(attempt is not None)
        assert attempt is not None
        require(
            attempt["state"] in {"creating", "open", "pending", "needs_reconcile", "completed"}
            and isinstance(attempt["provider_session_id"], str)
        )
        checkout = self.gateway.retrieve_checkout(attempt["provider_session_id"])
        require(
            checkout.get("id") == attempt["provider_session_id"]
            and checkout.get("livemode") is False
            and checkout.get("mode") == "subscription"
            and checkout.get("status") == "complete"
            and checkout.get("payment_status") in {"paid", "no_payment_required"}
            and checkout.get("customer") == customer
            and checkout.get("subscription") == sub_id
            and checkout.get("client_reference_id") == str(attempt_id)
        )
        lines = invoice.get("lines") or {}
        require(lines.get("has_more") is False and len(lines.get("data", [])) == 1)
        line = lines["data"][0]
        price_id = ((line.get("pricing") or {}).get("price_details") or {}).get("price")
        plan = next((p for p, i in self.gateway.prices.items() if i == price_id), None)
        require(
            plan is not None
            and line.get("quantity") == 1
            and line.get("currency") == invoice.get("currency") == "eur"
            and ((line.get("parent") or {}).get("subscription_item_details") or {}).get(
                "subscription"
            )
            == sub_id
        )
        payments = self.gateway.list_invoice_payments(invoice=invoice["id"])
        require(len(payments) == 1)
        payment = payments[0]
        details = payment.get("payment") or {}
        require(
            payment.get("livemode") is False
            and payment.get("invoice") == invoice["id"]
            and payment.get("status") == "paid"
            and payment.get("amount_paid") == amount
            and payment.get("currency") == invoice["currency"]
            and details.get("type") == "payment_intent"
        )
        intent_id = details.get("payment_intent")
        require(isinstance(intent_id, str))
        intent = self.gateway.retrieve_payment_intent(intent_id)
        require(
            intent.get("id") == intent_id
            and intent.get("livemode") is False
            and intent.get("customer") == customer
            and intent.get("status") == "succeeded"
            and intent.get("amount_received") == amount
            and intent.get("currency") == invoice["currency"]
            and isinstance(intent.get("latest_charge"), str)
        )
        charge = self.gateway.retrieve_charge(intent["latest_charge"])
        require(
            charge.get("id") == intent["latest_charge"]
            and charge.get("livemode") is False
            and charge.get("customer") == customer
            and charge.get("payment_intent") == intent_id
            and charge.get("paid") is True
            and charge.get("status") == "succeeded"
            and charge.get("amount") == amount
            and charge.get("currency") == invoice["currency"]
            and (charge.get("payment_method_details") or {}).get("type") == "card"
        )
        # A refund cannot be assigned safely when one PI pays multiple invoices.
        allocations = self.gateway.list_invoice_payments(payment_intent=intent_id)
        require(
            len(allocations) == 1
            and allocations[0].get("id") == payment.get("id")
            and allocations[0].get("invoice") == invoice["id"]
        )
        return {
            "user_id": attempt["user_id"],
            "provider_payment_id": payment["id"],
            "provider_invoice_id": invoice["id"],
            "provider_payment_intent_id": intent_id,
            "provider_customer_id": customer,
            "provider_subscription_id": sub_id,
            "provider_charge_id": intent["latest_charge"],
            "plan_code": plan,
            "amount_minor": amount,
            "currency": invoice["currency"],
            "paid_at": timestamp((payment.get("status_transitions") or {}).get("paid_at")),
            "livemode": False,
        }

    @staticmethod
    def persist(s, fact: dict) -> UUID:
        # Serialize duplicate facts AND refund totals, without granting UPDATE.
        s.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:k,0))"),
            {"k": "payment:" + fact["provider_payment_intent_id"]},
        )
        s.execute(
            text("""
INSERT INTO studio.payments(user_id,provider_payment_id,provider_invoice_id,
provider_payment_intent_id,provider_customer_id,provider_subscription_id,provider_charge_id,
plan_code,amount_minor,currency,paid_at,livemode)
VALUES(:user_id,:provider_payment_id,:provider_invoice_id,:provider_payment_intent_id,
:provider_customer_id,:provider_subscription_id,:provider_charge_id,:plan_code,:amount_minor,
:currency,:paid_at,:livemode) ON CONFLICT(provider_payment_id) DO NOTHING
"""),
            fact,
        )
        row = (
            s.execute(
                text("SELECT * FROM studio.payments WHERE provider_payment_id=:p"),
                {"p": fact["provider_payment_id"]},
            )
            .mappings()
            .one()
        )
        require(all(row[key] == value for key, value in fact.items()))
        return row["id"]

    def refund(self, worker, event: dict) -> None:
        refund = self.gateway.retrieve_refund(event["object_id"])
        require(refund.get("id") == event["object_id"] and refund.get("object") == "refund")
        # Refund has no livemode field. Mode and bindings are checked on PI/Charge.
        intent_id, charge_id = refund.get("payment_intent"), refund.get("charge")
        require(isinstance(intent_id, str) and isinstance(charge_id, str))
        allocations = self.gateway.list_invoice_payments(payment_intent=intent_id)
        require(len(allocations) == 1)
        invoice_id = allocations[0].get("invoice")
        require(isinstance(invoice_id, str))
        invoice = self.gateway.retrieve_invoice(invoice_id)
        require(invoice.get("id") == invoice_id)
        fact = self.prepare(invoice)
        require(fact is not None)
        assert fact is not None
        require(
            fact["provider_payment_intent_id"] == intent_id
            and fact["provider_charge_id"] == charge_id
            and refund.get("currency") == fact["currency"]
        )
        # Acquire a durable customer lease, then re-fetch current refund status.
        # Old deliveries cannot overwrite a newer status; no DB lock spans network.
        from uuid import uuid4

        token = uuid4()
        with self.transaction() as s:
            owner = s.scalar(
                text("""UPDATE studio.billing_customers
SET reconcile_token=:t,reconcile_until=now()+interval '60 seconds'
WHERE user_id=:u AND (reconcile_until IS NULL OR reconcile_until<now()) RETURNING user_id"""),
                {"t": token, "u": fact["user_id"]},
            )
            require(owner is not None)
        event["customer_token"], event["owner"] = token, owner
        current = self.gateway.retrieve_refund(event["object_id"])
        # Only status may change between reads.
        for key in ("id", "object", "payment_intent", "charge", "amount", "currency", "created"):
            require(current.get(key) == refund.get(key))
        status = current.get("status")
        require(status in {"succeeded", "pending", "requires_action", "failed", "canceled"})
        amount = positive(current.get("amount"))
        created = timestamp(current.get("created"))
        with self.transaction() as s:
            require(
                s.scalar(
                    text("""SELECT 1 FROM studio.billing_customers
WHERE user_id=:u AND reconcile_token=:t AND reconcile_until>now() FOR UPDATE"""),
                    {"u": owner, "t": token},
                )
                == 1
            )
            self.fence(s, event)
            payment_id = self.persist(s, fact)
            fields = {
                "payment_id": payment_id,
                "user_id": fact["user_id"],
                "provider_refund_id": current["id"],
                "amount_minor": amount,
                "currency": fact["currency"],
                "created_at": created,
            }
            previous = (
                s.execute(
                    text("SELECT * FROM studio.payment_refunds WHERE provider_refund_id=:r"),
                    {"r": current["id"]},
                )
                .mappings()
                .one_or_none()
            )
            if previous:
                require(all(previous[k] == v for k, v in fields.items()))
            require(amount <= fact["amount_minor"])
            if status == "succeeded":
                total = s.scalar(
                    text("""SELECT COALESCE(sum(amount_minor),0)
FROM studio.payment_refunds WHERE payment_id=:p AND status='succeeded' AND provider_refund_id<>:r"""),
                    {"p": payment_id, "r": current["id"]},
                )
                require(total + amount <= fact["amount_minor"])
            s.execute(
                text("""INSERT INTO studio.payment_refunds
(payment_id,user_id,provider_refund_id,amount_minor,currency,created_at,status)
VALUES(:payment_id,:user_id,:provider_refund_id,:amount_minor,:currency,:created_at,:status)
ON CONFLICT(provider_refund_id) DO UPDATE SET status=EXCLUDED.status"""),
                {**fields, "status": status},
            )
            worker._finish(s, event)
            s.execute(
                text("""UPDATE studio.billing_customers SET reconcile_token=NULL,reconcile_until=NULL
WHERE user_id=:u AND reconcile_token=:t"""),
                {"u": owner, "t": token},
            )

    @staticmethod
    def fence(s, event: dict) -> None:
        require(
            s.scalar(
                text("""SELECT 1 FROM studio_private.webhook_events
WHERE event_id=:e AND lease_token=:t AND lease_until>now() FOR UPDATE"""),
                {"e": event["event_id"], "t": event["lease_token"]},
            )
            == 1
        )


def payment_history(web_transaction, actor, *, limit: int = 25, before: UUID | None = None) -> dict:
    """Keyset cursor is owned local UUID; query under web RLS, independent of paid access."""
    require(1 <= limit <= 100)
    with web_transaction(actor) as s:
        params = {"u": actor.user_id, "limit": limit + 1}
        where = ""
        if before is not None:
            cursor = s.execute(
                text("SELECT paid_at,id FROM studio.payments WHERE id=:i AND user_id=:u"),
                {"i": before, "u": actor.user_id},
            ).one_or_none()
            if cursor is None:
                return {"payments": [], "next_cursor": None}
            params.update({"paid": cursor.paid_at, "id": cursor.id})
            where = " AND (paid_at,id)<(:paid,:id)"
        records = (
            s.execute(
                text(
                    """SELECT id,plan_code,amount_minor,currency,paid_at,recorded_at,livemode
FROM studio.payments WHERE user_id=:u"""
                    + where
                    + " ORDER BY paid_at DESC,id DESC LIMIT :limit"
                ),
                params,
            )
            .mappings()
            .all()
        )
        result = []
        for row in records[:limit]:
            # A bounded per-payment query keeps SQL simple; at most 100 payments.
            refunds = (
                s.execute(
                    text("""SELECT id,amount_minor,currency,created_at,status,
sum(CASE WHEN status='succeeded' THEN amount_minor ELSE 0 END) OVER() AS refunded_total
FROM studio.payment_refunds WHERE payment_id=:p AND user_id=:u
ORDER BY created_at DESC,id DESC LIMIT 101"""),
                    {"p": row["id"], "u": actor.user_id},
                )
                .mappings()
                .all()
            )
            total = int(refunds[0]["refunded_total"]) if refunds else 0
            status = (
                "refunded"
                if total == row["amount_minor"]
                else "partially_refunded"
                if total
                else "paid"
            )
            result.append(
                {
                    **row,
                    "status": status,
                    "refunded_minor": total,
                    "refunds": [
                        {k: v for k, v in r.items() if k != "refunded_total"} for r in refunds[:100]
                    ],
                    "refunds_has_more": len(refunds) > 100,
                }
            )
        return {
            "payments": result,
            "next_cursor": str(result[-1]["id"]) if len(records) > limit else None,
        }
