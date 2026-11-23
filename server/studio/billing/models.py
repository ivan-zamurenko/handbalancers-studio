"""Billing state is operator-only until a verified billing writer is implemented."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from studio.accounts.models import User
from studio.db import Base


class BillingCustomer(Base):
    __tablename__ = "billing_customers"
    __table_args__ = (
        UniqueConstraint("provider_customer_id", name="uq_billing_customer_provider"),
        CheckConstraint(
            "length(provider_customer_id) BETWEEN 1 AND 255", name="ck_billing_customer_provider"
        ),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey(User.id), primary_key=True)
    provider_customer_id: Mapped[str] = mapped_column(Text, nullable=False)
    reconcile_token: Mapped[UUID | None]
    reconcile_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Subscription(Base):
    """One current projection per customer; provider event history belongs to billing ingestion."""

    __tablename__ = "subscriptions"
    __table_args__ = (
        UniqueConstraint("provider_subscription_id", name="uq_subscription_provider"),
        CheckConstraint(
            "length(provider_subscription_id) BETWEEN 1 AND 255", name="ck_subscription_provider"
        ),
        CheckConstraint(
            "plan_code IN ('essential', 'plus', 'pro', 'pro-plus')", name="ck_subscription_plan"
        ),
        CheckConstraint(
            "status IN ('active', 'trialing', 'past_due', 'unpaid', 'canceled', "
            "'paused', 'incomplete', 'incomplete_expired')",
            name="ck_subscription_status",
        ),
        CheckConstraint(
            "status <> 'trialing' OR plan_code IN ('essential', 'plus')",
            name="ck_subscription_trial_plan",
        ),
        CheckConstraint(
            "isfinite(current_period_start) AND isfinite(current_period_end) "
            "AND current_period_end > current_period_start",
            name="ck_subscription_period",
        ),
        CheckConstraint("row_version > 0", name="ck_subscription_version"),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey(BillingCustomer.user_id), primary_key=True)
    provider_subscription_id: Mapped[str] = mapped_column(Text, nullable=False)
    plan_code: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))


class CheckoutAttempt(Base):
    __tablename__ = "checkout_attempts"
    __table_args__ = (
        CheckConstraint("discovery_attempts BETWEEN 0 AND 5", name="ck_checkout_discovery"),
        UniqueConstraint("id", "user_id", name="uq_checkout_owner"),
        UniqueConstraint("user_id", "idempotency_key", name="uq_checkout_key"),
        UniqueConstraint("provider_session_id", name="uq_checkout_session"),
        CheckConstraint("length(idempotency_key) BETWEEN 1 AND 128", name="ck_checkout_key"),
        CheckConstraint(
            "plan_code IN ('essential','plus','pro','pro-plus')", name="ck_checkout_plan"
        ),
        CheckConstraint(
            "state IN ('creating','open','pending','completed','expired','failed','needs_reconcile')",
            name="ck_checkout_state",
        ),
        CheckConstraint(
            "isfinite(created_at) AND isfinite(expires_at) AND expires_at > created_at",
            name="ck_checkout_time",
        ),
        CheckConstraint("length(terms_version) BETWEEN 1 AND 100", name="ck_checkout_terms"),
        Index(
            "uq_checkout_active",
            "user_id",
            unique=True,
            postgresql_where=text("state IN ('creating','open','pending','needs_reconcile')"),
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey(User.id), nullable=False)
    trial_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    discovery_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    next_discovery: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    plan_code: Mapped[str] = mapped_column(Text, nullable=False)
    terms_version: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'creating'"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    provider_session_id: Mapped[str | None] = mapped_column(Text)
    checkout_url: Mapped[str | None] = mapped_column(Text)


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    __table_args__ = (
        CheckConstraint("length(event_id) BETWEEN 4 AND 255", name="ck_webhook_event_id"),
        CheckConstraint("length(object_id) BETWEEN 1 AND 255", name="ck_webhook_object_id"),
        CheckConstraint("length(event_type) BETWEEN 1 AND 100", name="ck_webhook_type"),
        CheckConstraint(
            "state IN ('pending','processing','processed','failed','ignored')",
            name="ck_webhook_state",
        ),
        CheckConstraint("attempts BETWEEN 0 AND 10", name="ck_webhook_attempts"),
        Index("ix_webhook_retry", "state", "next_retry"),
        {"schema": "studio_private"},
    )
    event_id: Mapped[str] = mapped_column(Text, primary_key=True)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    object_id: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_payload: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'pending'"))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    next_retry: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    lease_token: Mapped[UUID | None]
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class TrialClaim(Base):
    __tablename__ = "trial_claims"
    __table_args__ = (
        ForeignKeyConstraint(
            ["attempt_id", "user_id"],
            ["studio.checkout_attempts.id", "studio.checkout_attempts.user_id"],
            name="fk_trial_attempt_owner",
        ),
        UniqueConstraint("attempt_id", name="uq_trial_attempt"),
        CheckConstraint("state IN ('reserved','claimed','released')", name="ck_trial_state"),
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey(User.id), primary_key=True)
    attempt_id: Mapped[UUID] = mapped_column(nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("provider_payment_id", name="uq_payment_provider"),
        UniqueConstraint("provider_payment_intent_id", name="uq_payment_intent"),
        UniqueConstraint("id", "user_id", name="uq_payment_owner"),
        CheckConstraint(
            "plan_code IN ('essential','plus','pro','pro-plus')", name="ck_payment_plan"
        ),
        CheckConstraint("amount_minor > 0", name="ck_payment_amount"),
        CheckConstraint("currency ~ '^[a-z]{3}$'", name="ck_payment_currency"),
        CheckConstraint("isfinite(paid_at) AND isfinite(recorded_at)", name="ck_payment_time"),
        Index("ix_payment_owner_time", "user_id", "paid_at", "id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey(BillingCustomer.user_id), nullable=False)
    provider_payment_id: Mapped[str] = mapped_column(Text, nullable=False)
    provider_invoice_id: Mapped[str] = mapped_column(Text, nullable=False)
    provider_payment_intent_id: Mapped[str] = mapped_column(Text, nullable=False)
    provider_customer_id: Mapped[str] = mapped_column(Text, nullable=False)
    provider_subscription_id: Mapped[str] = mapped_column(Text, nullable=False)
    provider_charge_id: Mapped[str] = mapped_column(Text, nullable=False)
    plan_code: Mapped[str] = mapped_column(Text, nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(Text, nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    livemode: Mapped[bool] = mapped_column(Boolean, nullable=False)


class PaymentRefund(Base):
    __tablename__ = "payment_refunds"
    __table_args__ = (
        ForeignKeyConstraint(
            ["payment_id", "user_id"],
            ["studio.payments.id", "studio.payments.user_id"],
            name="fk_refund_payment_owner",
        ),
        UniqueConstraint("provider_refund_id", name="uq_refund_provider"),
        CheckConstraint(
            "status IN ('pending','requires_action','succeeded','failed','canceled')",
            name="ck_refund_status",
        ),
        CheckConstraint("amount_minor > 0", name="ck_refund_amount"),
        CheckConstraint("currency ~ '^[a-z]{3}$'", name="ck_refund_currency"),
        CheckConstraint("isfinite(created_at) AND isfinite(recorded_at)", name="ck_refund_time"),
        Index("ix_refund_payment", "payment_id", "user_id"),
        Index("ix_refund_owner", "user_id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    payment_id: Mapped[UUID] = mapped_column(nullable=False)
    user_id: Mapped[UUID] = mapped_column(nullable=False)
    provider_refund_id: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
