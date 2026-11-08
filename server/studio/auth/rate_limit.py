"""Atomic minute budgets shared by workers, bounded by the existing storage ceiling."""

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class AuthLimits:
    client: int = 10
    account: int = 10

    def __post_init__(self) -> None:
        if not all(
            type(value) is int and 1 <= value <= 10 for value in (self.client, self.account)
        ):
            raise ValueError("Invalid auth quota")


def allow_start(session: Session, bucket_hash: str, *, limit: int = 10) -> bool:
    if not 1 <= limit <= 10:
        raise ValueError("Invalid auth quota")
    # Never lower an existing counter when workers use different admission limits.
    count = session.execute(
        text("""
INSERT INTO studio_private.auth_rate_limits (bucket_hash, window_start, attempts)
VALUES (:bucket, clock_timestamp(), 1)
ON CONFLICT (bucket_hash) DO UPDATE SET
    attempts=CASE WHEN auth_rate_limits.window_start < clock_timestamp()-interval '1 minute'
        THEN 1 ELSE LEAST(auth_rate_limits.attempts+1,11) END,
    window_start=CASE WHEN auth_rate_limits.window_start < clock_timestamp()-interval '1 minute'
        THEN clock_timestamp() ELSE auth_rate_limits.window_start END
RETURNING attempts
"""),
        {"bucket": bucket_hash},
    ).scalar_one()
    return count <= limit
