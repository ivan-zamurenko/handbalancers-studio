"""S04-04: product identity = Supabase auth UUID; no own email-based linking or merge."""

import asyncio

import pytest
from sqlalchemy import text
from studio.auth.jwt import InvalidIdentity

from server.tests.integration.auth import test_oauth_flow as flow_support
from server.tests.integration.database.test_auth_storage import (  # noqa: F401
    database_engine,
    storage_db,
)

flow = flow_support.flow


def login(service, **user_patch):
    """Real finish(); only the synthetic Supabase exchange payload is altered."""
    original = service.gateway.oauth_exchange

    async def exchange(code, verifier):
        payload = await original(code, verifier)
        payload["user"] = {**payload["user"], **user_patch}
        return {k: v for k, v in payload.items()}

    service.gateway.oauth_exchange = exchange
    try:
        start = service.start("google", "/plans")
        return asyncio.run(
            service.finish("google", start.attempt, start.binding.get_secret_value(), "code")
        )
    finally:
        service.gateway.oauth_exchange = original


def rows(db, sql, **params):
    with db.connect() as conn:
        return conn.execute(text(sql), params).all()


def test_same_auth_uuid_same_profile(flow):
    service, _, db, auth_id = flow
    google = login(service, email="ivan@gmail.test", app_metadata={"provider": "google"})
    password = login(service, email="ivan@gmail.test", app_metadata={"provider": "email"})
    assert google.user_id == password.user_id
    assert rows(db, "SELECT id FROM studio.users WHERE auth_user_id=:a", a=auth_id) == [
        (google.user_id,)
    ]


def test_unverified_claim_no_link(flow):
    service, _, db, auth_id = flow
    with pytest.raises(InvalidIdentity):
        login(service, email_confirmed_at=None, email="victim@example.test")
    assert rows(db, "SELECT id FROM studio.users WHERE auth_user_id=:a", a=auth_id) == []
    sessions = (
        "SELECT 1 FROM studio_private.web_sessions s "
        "JOIN studio.users u ON u.id = s.user_id WHERE u.auth_user_id=:a"
    )
    assert rows(db, sessions, a=auth_id) == []


def test_email_not_primary_key(flow):
    service, _, db, _ = flow
    before = login(service, email="old@example.test")
    after = login(service, email="new@example.test")
    assert before.user_id == after.user_id
    columns = rows(
        db,
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='studio' AND table_name='users' AND column_name ILIKE '%email%'",
    )
    assert columns == []


def test_conflict_no_auto_merge(flow):
    service, calls, db, auth_id = flow
    existing = login(service, email="ivan@example.test")
    other = "00000000-0000-4000-8000-000000000042"
    # Payload user differs from the signed JWT subject: reject, never merge by email.
    with pytest.raises(InvalidIdentity):
        login(service, id=other, email="ivan@example.test")
    assert rows(db, "SELECT id FROM studio.users WHERE auth_user_id=:a", a=other) == []
    assert rows(db, "SELECT id FROM studio.users WHERE auth_user_id=:a", a=auth_id) == [
        (existing.user_id,)
    ]
    assert len(calls) == 2
