"""DB-backed fixed-window quota: ten starts/client/minute across app workers."""

from sqlalchemy import text
from sqlalchemy.orm import Session


def allow_start(session: Session, bucket_hash: str, *, limit: int = 10) -> bool:
    if not 1 <= limit <= 10:
        raise ValueError("Invalid auth quota")
    count = session.execute(
        text("""
INSERT INTO studio_private.auth_rate_limits (bucket_hash, window_start, attempts)
VALUES (:bucket, clock_timestamp(), 1)
ON CONFLICT (bucket_hash) DO UPDATE SET
    attempts=CASE WHEN auth_rate_limits.window_start < clock_timestamp()-interval '1 minute'
        THEN 1 ELSE LEAST(auth_rate_limits.attempts+1,:ceiling) END,
    window_start=CASE WHEN auth_rate_limits.window_start < clock_timestamp()-interval '1 minute'
        THEN clock_timestamp() ELSE auth_rate_limits.window_start END
RETURNING attempts
"""),
        {"bucket": bucket_hash, "ceiling": limit + 1},
    ).scalar_one()
    return count <= limit
