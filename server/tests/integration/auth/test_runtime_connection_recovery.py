"""Real local PostgreSQL disconnections and timeouts; never touch hosted connections."""

import base64
from contextlib import contextmanager
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from studio import db
from studio.auth import runtime
from studio.settings import Settings
from studio.shared.context import Actor

from server.tests.integration.auth import test_auth_resilience as support
from server.tests.integration.database import test_auth_storage as storage_support

flow = support.flow
database_engine = storage_support.database_engine
storage_db = storage_support.storage_db


@pytest.mark.parametrize("kind", ["auth", "web"])
def test_stale_runtime_connection_recovers_before_transaction(storage_db, monkeypatch, kind):
    engines = []
    role = "studio_auth_runtime" if kind == "auth" else "studio_web"

    def local_engine(url, **options):
        # Production factory options, real local DB, narrow role on each connection.
        engine = create_engine(url, **options)
        engines.append(engine)

        @event.listens_for(engine, "connect")
        def set_role(connection, _):
            with connection.cursor() as cursor:
                cursor.execute("SET ROLE " + role)
            connection.commit()

        return engine

    monkeypatch.setattr(runtime if kind == "auth" else db, "create_engine", local_engine)
    url = storage_db.url.render_as_string(hide_password=False)
    settings = Settings(
        app_env="test",
        database_url=url,
        auth_database_url=url,
        auth_email_enabled=True,
        token_encryption_key=base64.b64encode(b"a" * 32).decode(),
        public_origin="https://studio.example.test",
        supabase_url="https://auth.example.test",
        supabase_publishable_key="synthetic-key",
    )
    actor = Actor(uuid4())
    if kind == "auth":
        service = runtime.build_oauth(settings)
        transaction = service.transaction
    else:
        web_transaction = db.web_transaction_factory(settings)
        transaction = lambda: web_transaction(actor)

    try:
        with transaction() as session:
            old_pid = session.scalar(text("SELECT pg_backend_pid()"))
            driver = session.connection().connection.driver_connection
        # Close AFTER check-in: pool still believes its idle connection is usable.
        driver.close()
        with transaction() as session:
            assert session.scalar(text("SELECT pg_backend_pid()")) != old_pid
            assert session.scalar(text("SELECT current_user")) == role
            if kind == "web":
                assert session.scalar(text("SELECT current_setting('studio.user_id')")) == str(
                    actor.user_id
                )
    finally:
        for engine in engines:
            engine.dispose()


@pytest.mark.parametrize("path", ["/api/session", "/dashboard", "/progress"])
def test_final_session_read_timeout_is_retryable_without_logout(flow, path, caplog):
    service, calls, _, _ = flow
    cookie = support.signed_session(service)
    transaction = service.transaction
    transactions = 0

    @contextmanager
    def fail_final_read_once():
        nonlocal transactions
        transactions += 1
        with transaction() as session:
            if transactions == 2:
                # Real DB exception after refresh/JWT succeeded, during final recheck.
                session.execute(text("SET LOCAL statement_timeout='10ms'"))
                session.execute(text("SELECT pg_sleep(0.1) /* synthetic-private-marker */"))
            yield session

    service.transaction = fail_final_read_once
    with TestClient(support.app_for(service), base_url=service.public_origin) as client:
        client.cookies.set("__Host-studio_session", cookie)
        result = client.get(path, follow_redirects=False)
        assert result.status_code == 503
        assert "no-store" in result.headers["cache-control"]
        assert "set-cookie" not in result.headers
        assert "data-member-shell" not in result.text
        assert transactions == 2  # No silent replay of a failed transaction.
        assert "synthetic-private-marker" not in result.text + caplog.text
        assert cookie not in result.text + caplog.text
        retried = client.get("/api/session")
        assert retried.status_code == 200
        assert retried.json()["authenticated"] is True
    assert len(calls) == 1  # Initial login exchange only, no unnecessary token rotation.
    with transaction() as session:
        assert service.store.read_session(session, cookie)
