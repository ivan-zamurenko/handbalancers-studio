"""Commit an owned intent before the network; retries retain the same provider key."""

from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from studio.accounts.onboarding import setup_required
from studio.accounts.service import WebTransaction
from studio.billing.catalog import PLANS
from studio.shared.context import Actor

BillingTransaction = Callable[[], AbstractContextManager[Session]]
ACTIVE_STATES = ("creating", "open", "pending", "needs_reconcile")


class CheckoutConflict(ValueError):
    pass


class CheckoutForbidden(ValueError):
    pass


class CheckoutNotFound(ValueError):
    pass


def lock_customer(session: Session, user_id: UUID) -> None:
    session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:u,13))"), {"u": str(user_id)}
    )


def view(row: Any) -> dict[str, Any]:
    return {name: row[name] for name in ("id", "plan_code", "state", "checkout_url", "expires_at")}


class CheckoutService:
    def __init__(
        self,
        *,
        transaction: BillingTransaction,
        web_transaction: WebTransaction,
        gateway: Any,
        origin: str,
    ):
        self.transaction = transaction
        self.web_transaction = web_transaction
        self.gateway = gateway
        self.origin = origin.rstrip("/")

    def begin(
        self, actor: Actor, *, plan_code: str, terms_version: str, key: str
    ) -> dict[str, Any]:
        if plan_code not in PLANS or terms_version != "test-v1" or not 1 <= len(key) <= 128:
            raise CheckoutForbidden()
        if setup_required(self.web_transaction, actor):
            raise CheckoutForbidden()
        now = datetime.now(UTC)
        with self.transaction() as session:
            lock_customer(session, actor.user_id)
            row = (
                session.execute(
                    text(
                        "SELECT * FROM studio.checkout_attempts WHERE user_id=:u AND idempotency_key=:k"
                    ),
                    {"u": actor.user_id, "k": key},
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                row = (
                    session.execute(
                        text(
                            "SELECT * FROM studio.checkout_attempts WHERE user_id=:u AND state IN ('creating','open','pending','needs_reconcile')"
                        ),
                        {"u": actor.user_id},
                    )
                    .mappings()
                    .one_or_none()
                )
            if row is not None:
                if row["idempotency_key"] != key:
                    raise CheckoutConflict()
                if (row["plan_code"], row["terms_version"]) != (plan_code, terms_version):
                    raise CheckoutConflict()
                if row["state"] != "creating":
                    return view(row)
            else:
                if session.scalar(
                    text(
                        "SELECT 1 FROM studio.subscriptions WHERE user_id=:u AND status IN ('active','trialing') AND current_period_end>:n"
                    ),
                    {"u": actor.user_id, "n": now},
                ):
                    raise CheckoutConflict()
                row = (
                    session.execute(
                        text(
                            "INSERT INTO studio.checkout_attempts (id,user_id,idempotency_key,plan_code,terms_version,expires_at) VALUES (:i,:u,:k,:p,:t,:e) RETURNING *"
                        ),
                        {
                            "i": uuid4(),
                            "u": actor.user_id,
                            "k": key,
                            "p": plan_code,
                            "t": terms_version,
                            "e": now + timedelta(hours=2),
                        },
                    )
                    .mappings()
                    .one()
                )
            attempt = dict(row)
            customer = session.scalar(
                text("SELECT provider_customer_id FROM studio.billing_customers WHERE user_id=:u"),
                {"u": actor.user_id},
            )
        # Ambiguous expired calls need provider reconciliation, never a new key.
        if attempt["expires_at"] < now + timedelta(minutes=30):
            raise CheckoutConflict()
        if customer is None:
            customer = self.gateway.create_customer(actor.user_id)
            with self.transaction() as session:
                session.execute(
                    text(
                        "INSERT INTO studio.billing_customers(user_id,provider_customer_id) VALUES(:u,:c) ON CONFLICT(user_id) DO NOTHING"
                    ),
                    {"u": actor.user_id, "c": customer},
                )
                stored = session.scalar(
                    text(
                        "SELECT provider_customer_id FROM studio.billing_customers WHERE user_id=:u"
                    ),
                    {"u": actor.user_id},
                )
                if stored != customer:
                    raise CheckoutConflict()
        result = self.gateway.create_checkout(
            attempt_id=attempt["id"],
            customer_id=customer,
            plan_code=plan_code,
            trial=False,
            origin=self.origin,
            expires_at=int(attempt["expires_at"].timestamp()),
        )
        with self.transaction() as session:
            session.execute(
                text(
                    "UPDATE studio.checkout_attempts SET provider_session_id=:s,checkout_url=:url,state='open' WHERE id=:i AND user_id=:u AND state='creating'"
                ),
                {"s": result["id"], "url": result["url"], "i": attempt["id"], "u": actor.user_id},
            )
        return self.get(actor, attempt["id"])

    def get(self, actor: Actor, attempt_id: UUID) -> dict[str, Any]:
        with self.transaction() as session:
            row = (
                session.execute(
                    text("SELECT * FROM studio.checkout_attempts WHERE id=:i AND user_id=:u"),
                    {"i": attempt_id, "u": actor.user_id},
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                raise CheckoutNotFound()
            return view(row)
