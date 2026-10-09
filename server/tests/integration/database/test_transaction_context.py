"""Real PostgreSQL RLS and pool reuse, under a non-owner runtime role."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import DBAPIError

from server.tests.integration.database import test_migration_baseline as baseline

database_engine = baseline.engine

USER_A = UUID("00000000-0000-0000-0000-000000000001")
USER_B = UUID("00000000-0000-0000-0000-000000000002")


@pytest.fixture(scope="module", params=[1, 2])
def runtime(database_engine, request):
    with database_engine.begin() as connection:
        connection.execute(text("CREATE SCHEMA studio"))
        connection.execute(text("GRANT USAGE ON SCHEMA studio TO studio_web"))
        connection.execute(
            text(
                "CREATE TABLE studio.context_probe (user_id uuid PRIMARY KEY, value integer NOT NULL)"
            )
        )
        connection.execute(
            text("INSERT INTO studio.context_probe VALUES (:a, 0), (:b, 0)"),
            {"a": USER_A, "b": USER_B},
        )
        connection.execute(text("ALTER TABLE studio.context_probe ENABLE ROW LEVEL SECURITY"))
        connection.execute(
            text("""CREATE POLICY owner_only ON studio.context_probe TO studio_web
            USING (user_id = NULLIF(current_setting('studio.user_id', true), '')::uuid)
            WITH CHECK (user_id = NULLIF(current_setting('studio.user_id', true), '')::uuid)""")
        )
        connection.execute(text("GRANT SELECT, UPDATE ON studio.context_probe TO studio_web"))
    pooled = create_engine(
        database_engine.url,
        pool_size=request.param,
        max_overflow=0,
        pool_timeout=5,
        hide_parameters=True,
    )

    @event.listens_for(pooled, "connect")
    def runtime_role(connection, _):
        with connection.cursor() as cursor:
            cursor.execute("SET ROLE studio_web")
        connection.commit()

    yield pooled
    pooled.dispose()
    with database_engine.begin() as connection:
        connection.execute(text("DROP TABLE studio.context_probe"))
        connection.execute(text("DROP SCHEMA studio"))


def api():
    import studio.db as database

    assert hasattr(database, "command_transaction"), "Transaction context is not implemented"
    from studio.shared.context import Actor

    return database.command_transaction, Actor


def visible(session):
    assert session.scalar(text("SELECT current_user")) == "studio_web"
    return session.scalars(text("SELECT user_id FROM studio.context_probe")).all()


def assert_pool_clean(runtime, pid):
    with runtime.connect() as connection:
        assert connection.scalar(text("SELECT pg_backend_pid()")) == pid
        assert (
            connection.scalar(text("SELECT NULLIF(current_setting('studio.user_id', true), '')"))
            is None
        )
        assert connection.execute(text("SELECT * FROM studio.context_probe")).all() == []


def test_context_clears_after_commit(runtime):
    transaction, Actor = api()
    with transaction(runtime, Actor(USER_A)) as session:
        pid = session.scalar(text("SELECT pg_backend_pid()"))
        assert visible(session) == [USER_A]
        session.execute(text("UPDATE studio.context_probe SET value = 7"))
    assert_pool_clean(runtime, pid)
    with transaction(runtime, Actor(USER_B)) as session:
        assert visible(session) == [USER_B]
        assert session.scalar(text("SELECT value FROM studio.context_probe")) == 0
    with transaction(runtime, Actor(USER_A)) as session:
        assert session.scalar(text("SELECT value FROM studio.context_probe")) == 7


def test_context_clears_after_rollback(runtime):
    transaction, Actor = api()
    with pytest.raises(DBAPIError), transaction(runtime, Actor(USER_B)) as session:
        pid = session.scalar(text("SELECT pg_backend_pid()"))
        session.execute(text("UPDATE studio.context_probe SET value = 99"))
        session.execute(text("SELECT 1 / 0"))
    assert_pool_clean(runtime, pid)
    with transaction(runtime, Actor(USER_B)) as session:
        assert visible(session) == [USER_B]
        assert session.scalar(text("SELECT value FROM studio.context_probe")) == 0


def test_no_context_deny(runtime):
    transaction, _ = api()
    with transaction(runtime, None) as session:
        assert visible(session) == []
        assert session.execute(text("UPDATE studio.context_probe SET value = 100")).rowcount == 0


def test_concurrent_commands_do_not_share_actor(runtime):
    transaction, Actor = api()

    barrier = Barrier(2)

    def read(user_id):
        with transaction(runtime, Actor(user_id)) as session:
            if runtime.pool.size() == 2:
                barrier.wait(timeout=5)
            return session.scalar(text("SELECT pg_backend_pid()")), visible(session)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(read, [USER_A, USER_B] * 4))
    assert [rows for _, rows in results] == [[USER_A], [USER_B]] * 4
    assert len({pid for pid, _ in results}) == runtime.pool.size()
