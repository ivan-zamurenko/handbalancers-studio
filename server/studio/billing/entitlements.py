"""Pure policy plus a narrow database reader. No client tier, SDK or Request input."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from studio.billing.catalog import PLANS
from studio.billing.models import Subscription
from studio.shared.context import Actor


@dataclass(frozen=True, slots=True)
class SubscriptionProjection:
    """Trusted server value; constructing it alone does not verify a payment."""

    user_id: UUID
    plan_code: str
    status: str
    current_period_start: datetime
    current_period_end: datetime
    row_version: int


@dataclass(frozen=True, slots=True)
class Entitlements:
    """Own reads still require authentication and resource ownership at their boundary."""

    capabilities: frozenset[str] = frozenset()
    can_read_own_profile: bool = True
    can_read_own_history: bool = True


def load_subscription(session: Session, actor: Actor) -> SubscriptionProjection | None:
    """Read current committed projection inside the caller's command transaction.

    Column selection avoids returning a stale ORM identity-map instance. The caller
    must bind the authenticated actor to RLS, then recheck for every paid command.
    This read is not a lock or an authorization receipt for a later transaction.
    """
    row = (
        session.execute(
            select(
                Subscription.user_id,
                Subscription.plan_code,
                Subscription.status,
                Subscription.current_period_start,
                Subscription.current_period_end,
                Subscription.row_version,
            ).where(Subscription.user_id == actor.user_id)
        )
        .mappings()
        .one_or_none()
    )
    return SubscriptionProjection(**row) if row is not None else None


def evaluate_entitlements(
    *,
    actor: Actor,
    subscription: SubscriptionProjection | None,
    now: datetime,
    ready: frozenset[str] = frozenset(),
) -> Entitlements:
    """Effective rights = valid owned subscription ∩ plan capabilities ∩ readiness.

    Readiness comes from trusted server configuration, never request flags. No grace
    period is inferred. Trial eligibility/card/one-time use must be verified by the
    future billing ingestion boundary before it may write a trialing projection.
    """
    if not isinstance(actor, Actor):
        raise TypeError("A trusted actor is required")
    if subscription is not None and not isinstance(subscription, SubscriptionProjection):
        raise TypeError("A trusted subscription projection is required")
    if now.utcoffset() is None:
        raise ValueError("An aware evaluation timestamp is required")
    if subscription is None or subscription.user_id != actor.user_id:
        return Entitlements()
    plan = PLANS.get(subscription.plan_code)
    if (
        plan is None
        or subscription.status not in {"active", "trialing"}
        or (subscription.status == "trialing" and not plan.trial_allowed)
        or subscription.row_version < 1
        or subscription.current_period_start.utcoffset() is None
        or subscription.current_period_end.utcoffset() is None
        or not subscription.current_period_start <= now < subscription.current_period_end
    ):
        return Entitlements()
    return Entitlements(capabilities=plan.capabilities & ready)
