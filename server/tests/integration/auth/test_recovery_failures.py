"""Real DB cleanup/isolation; inject failures only at external I/O boundaries."""

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from studio.auth import recovery
from studio.auth.gateway import AuthFailure, AuthFailureKind
from studio.auth.jwt import InvalidIdentity
from studio.auth.token_store import StoreError

from server.tests.integration.auth import test_oauth_flow as flow_support
from server.tests.integration.database.test_auth_storage import (  # noqa: F401
    database_engine,
    storage_db,
)
from tools import local_stack

flow = flow_support.flow


@pytest.fixture
def prepared(flow, monkeypatch):
    service, _, engine, auth_id = flow
    payload = asyncio.run(service.gateway.oauth_exchange("synthetic", "synthetic"))
    issued = asyncio.run(service.accept_identity(payload))
    calls = []

    async def verify(*_):
        return payload

    async def update(*_):
        calls.append("update")
        return {"id": str(auth_id)}

    async def global_logout(*_):
        calls.append("global")

    async def cleanup(*_):
        calls.append("cleanup")

    monkeypatch.setattr(service.gateway, "verify_recovery", verify)
    monkeypatch.setattr(service.gateway, "update_password", update)
    monkeypatch.setattr(service.gateway, "logout_all", global_logout)
    monkeypatch.setattr(service.gateway, "logout", cleanup)
    return service, engine, issued, calls, payload


def run_confirm(service):
    return recovery.confirm_recovery(
        service, "member@example.test", "123456", "synthetic-new-password", client_key="test"
    )


def assert_retired(service, cookie):
    with service.transaction() as session, pytest.raises(StoreError):
        service.store.read_session(session, cookie)


def test_initial_db_failure_prevents_password_update(prepared, monkeypatch):
    service, _, _, calls, _ = prepared

    def failed(*_):
        raise OperationalError("synthetic", {}, Exception("offline"))

    monkeypatch.setattr(recovery, "retire_sessions", failed)
    with pytest.raises(OperationalError):
        asyncio.run(run_confirm(service))
    assert calls == ["cleanup"]


@pytest.mark.parametrize("operation", ["update_password", "logout_all"])
def test_provider_failure_retires_rows_and_never_returns_success(prepared, monkeypatch, operation):
    service, _, issued, calls, _ = prepared

    async def failed(*_):
        raise AuthFailure(AuthFailureKind.TIMEOUT)

    monkeypatch.setattr(service.gateway, operation, failed)
    with pytest.raises(AuthFailure):
        asyncio.run(run_confirm(service))
    assert_retired(service, issued.cookie.get_secret_value())
    assert calls[-1] == "cleanup"


def test_cancellation_cleans_up_and_propagates(prepared, monkeypatch):
    service, _, issued, calls, _ = prepared

    async def scenario():
        entered = asyncio.Event()

        async def wait(*_):
            entered.set()
            await asyncio.Future()

        monkeypatch.setattr(service.gateway, "update_password", wait)
        task = asyncio.create_task(run_confirm(service))
        await asyncio.wait_for(entered.wait(), 2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())
    assert_retired(service, issued.cookie.get_secret_value())
    assert calls == ["cleanup"]


@pytest.mark.parametrize("failure", ["timeout", "rejected", "wrong-user"])
def test_post_commit_live_check_failure_revokes_new_row(prepared, monkeypatch, failure):
    service, engine, _, _, payload = prepared
    with engine.connect() as connection:
        before = set(connection.scalars(text("SELECT id FROM studio_private.web_sessions")))

    async def failed(*_):
        if failure == "wrong-user":
            return {"id": str(uuid4())}
        kind = AuthFailureKind.TIMEOUT if failure == "timeout" else AuthFailureKind.REJECTED
        raise AuthFailure(kind)

    monkeypatch.setattr(service.gateway, "current_user", failed)
    with pytest.raises((AuthFailure, InvalidIdentity)):
        asyncio.run(service.accept_identity(payload))
    with engine.connect() as connection:
        rows = [
            row
            for row in connection.execute(
                text("SELECT id,revoked_at FROM studio_private.web_sessions")
            )
            if row.id not in before
        ]
        assert len(rows) == 1 and rows[0].revoked_at is not None


def test_recovery_does_not_revoke_another_account(prepared):
    service, engine, issued, _, _ = prepared
    other_auth = uuid4()
    local_stack.execute_local_sql(
        local_stack.verify_container("test"),
        f"\\connect {engine.url.database}\nINSERT INTO auth.users VALUES ('{other_auth}');",
    )
    # Reuse encrypted session creation with a distinct, valid product owner.
    with service.transaction() as session:
        original = service.store.read_session(session, issued.cookie.get_secret_value())
        other_id = session.scalar(
            text("SELECT studio_private.provision_member(:id,NULL,NULL,'uk','UTC')"),
            {"id": other_auth},
        )
        from datetime import UTC, datetime, timedelta

        other = service.store.create_session(
            session,
            user_id=other_id,
            upstream_session_id=uuid4(),
            access_token="synthetic-other",
            refresh_token="synthetic-other-refresh",
            access_expires_at=original.access_expires_at,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
    asyncio.run(run_confirm(service))
    assert_retired(service, issued.cookie.get_secret_value())
    with service.transaction() as session:
        assert (
            service.store.read_session(session, other.cookie.get_secret_value()).user_id == other_id
        )
