"""Reservation/confirmation are transaction-local; redirects never consume trials."""

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from studio.billing.catalog import PLANS
from studio.billing.checkout import CheckoutConflict


def reserve(session: Session, user_id: UUID, attempt_id: UUID, plan_code: str) -> bool:
    if not PLANS[plan_code].trial_allowed:
        return False
    row = session.execute(
        text("SELECT state FROM studio.trial_claims WHERE user_id=:u FOR UPDATE"), {"u": user_id}
    ).one_or_none()
    if row is not None and row.state == "claimed":
        return False
    if row is not None and row.state == "reserved":
        raise CheckoutConflict()
    session.execute(
        text(
            "INSERT INTO studio.trial_claims(user_id,attempt_id,state) VALUES(:u,:a,'reserved') ON CONFLICT(user_id) DO UPDATE SET attempt_id=EXCLUDED.attempt_id,state='reserved',updated_at=now() WHERE studio.trial_claims.state='released'"
        ),
        {"u": user_id, "a": attempt_id},
    )
    return True


def confirm(session: Session, user_id: UUID, attempt: Any, subscription: dict[str, Any]) -> None:
    has_trial = subscription.get("trial_start") is not None
    if bool(attempt["trial_enabled"]) != has_trial:
        raise CheckoutConflict()
    if not has_trial:
        return
    start, end = subscription.get("trial_start"), subscription.get("trial_end")
    if type(start) is not int or type(end) is not int or not 0 < end - start <= 7 * 86400:
        raise CheckoutConflict()
    changed = session.scalar(
        text(
            "UPDATE studio.trial_claims SET state='claimed',updated_at=now() WHERE user_id=:u AND attempt_id=:a AND state='reserved' RETURNING user_id"
        ),
        {"u": user_id, "a": attempt["id"]},
    )
    if changed is None:
        state = session.scalar(
            text("SELECT state FROM studio.trial_claims WHERE user_id=:u AND attempt_id=:a"),
            {"u": user_id, "a": attempt["id"]},
        )
        if state != "claimed":
            raise CheckoutConflict()


def release(session: Session, attempt_id: UUID) -> None:
    session.execute(
        text(
            "UPDATE studio.trial_claims SET state='released',updated_at=now() WHERE attempt_id=:a AND state='reserved'"
        ),
        {"a": attempt_id},
    )
