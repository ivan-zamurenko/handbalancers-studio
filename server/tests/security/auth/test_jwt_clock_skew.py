"""Allow at most one second of iat skew; expiry/nbf/signature remain strict."""

import asyncio
from datetime import UTC, datetime

import jwt
import pytest
from studio.auth.jwt import InvalidIdentity

from server.tests.security.auth.test_jwt_validation import USER, make_validator, signed


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    from studio.auth import jwt as module

    now = 1_800_000_000.99

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.fromtimestamp(now, tz or UTC)

    monkeypatch.setattr(jwt.api_jwt, "datetime", Clock)
    monkeypatch.setattr(module.time, "time", lambda: now)
    return now


def test_small_issuer_clock_skew_does_not_reject_signed_identity(fixed_clock):
    validator, _ = make_validator()
    identity = asyncio.run(validator.verify(signed(iat=int(fixed_clock) + 1)))
    assert str(identity.user_id) == USER


@pytest.mark.parametrize(
    "changes",
    [
        {"iat": 1_800_000_002},  # Over the one-second bound.
        {"iat": 1_800_000_001, "exp": 1_800_000_000},  # Already expired.
        {"iat": 1_800_000_001, "nbf": 1_800_000_001},  # Not yet valid.
        {"iat": "1800000000"},
        {"iat": True},
        {"iat": 1_800_000_000.5},
        {"iat": None},
    ],
)
def test_other_time_guards_remain_strict(changes):
    validator, _ = make_validator()
    with pytest.raises(InvalidIdentity):
        asyncio.run(validator.verify(signed(**changes)))
