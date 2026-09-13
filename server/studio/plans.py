"""Server-owned catalogue; an incoming price, currency or user ID is never accepted."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Plan:
    id: str
    price_cents: int
    currency: str = "EUR"


PLANS = {
    plan.id: plan
    for plan in (
        Plan("essential", 1999),
        Plan("plus", 4999),
        Plan("pro", 17999),
        Plan("pro_plus", 29999),
    )
}


def public_plans():
    return [asdict(plan) for plan in PLANS.values()]
