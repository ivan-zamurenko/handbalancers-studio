"""Denied IPs must not create attacker-controlled email buckets in PostgreSQL."""

import pytest
from sqlalchemy import text
from studio.auth.oauth import OAuthRateLimited
from studio.auth.verification import quota

from server.tests.integration.auth import test_oauth_flow as flow_support
from server.tests.integration.database.test_auth_storage import (  # noqa: F401
    database_engine,
    storage_db,
)

flow = flow_support.flow


@pytest.mark.parametrize("action", ["password-login", "verify", "resend"])
def test_denied_client_cannot_grow_account_buckets(flow, action):
    service, _, engine, _ = flow

    def count():
        with engine.connect() as connection:
            return connection.scalar(text("SELECT count(*) FROM studio_private.auth_rate_limits"))

    before = count()
    for number in range(10):
        quota(service, action, f"allowed-{number}@example.test", "same-client")
    assert count() == before + 11  # One IP budget plus ten account budgets.
    for number in range(5):
        with pytest.raises(OAuthRateLimited):
            quota(service, action, f"denied-{number}@example.test", "same-client")
    assert count() == before + 11

    # The exhausted account budget remains effective from a different client.
    if action == "resend":
        with pytest.raises(OAuthRateLimited):
            quota(service, action, "allowed-0@example.test", "other-client")
