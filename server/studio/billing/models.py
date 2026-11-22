"""Billing state is operator-only until a verified billing writer is implemented."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Text, UniqueConstraint, text
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
