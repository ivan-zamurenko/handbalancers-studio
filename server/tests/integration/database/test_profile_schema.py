"""Profile invariants on PostgreSQL, independent of future auth commands."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from server.tests.integration.database import test_migration_baseline as baseline
from tools import local_stack

database_engine = baseline.engine


@pytest.fixture(scope="module")
def profiles(database_engine):
    container = local_stack.verify_container("test")
    # This disposable fixture database is not the managed Supabase database.
    local_stack.execute_local_sql(
        container,
        rf"""
\connect {database_engine.url.database}
GRANT USAGE ON SCHEMA auth TO migration_owner;
GRANT REFERENCES (id) ON auth.users TO migration_owner;
INSERT INTO auth.users SELECT ('00000000-0000-0000-0000-' || lpad(i::text, 12, '0'))::uuid
FROM generate_series(1, 20) AS i;
""",
    )
    with database_engine.begin() as connection:
        before = connection.scalar(text("SELECT 'auth.users'::regclass::oid"))
        command.upgrade(baseline.configuration(connection), "0002")
        assert connection.scalar(text("SELECT to_regclass('studio.users')")) is not None, (
            "Product profile table absent"
        )
        command.upgrade(baseline.configuration(connection), "0002")
        assert connection.scalar(text("SELECT 'auth.users'::regclass::oid")) == before
    yield database_engine


def auth_id(number):
    return UUID(f"00000000-0000-0000-0000-{number:012}")


def insert(connection, number, **overrides):
    values = {
        "auth_user_id": auth_id(number),
        "locale": "uk",
        "timezone": "Europe/Kyiv",
        **overrides,
    }
    columns = ", ".join(values)
    parameters = ", ".join(":" + name for name in values)
    return (
        connection.execute(
            text(f"INSERT INTO studio.users ({columns}) VALUES ({parameters}) RETURNING *"), values
        )
        .mappings()
        .one()
    )


def test_auth_user_unique(profiles):
    barrier = Barrier(2)

    def create():
        try:
            with profiles.begin() as connection:
                connection.execute(text("SET LOCAL statement_timeout = '5s'"))
                barrier.wait(timeout=5)
                insert(connection, 1)
            return "created"
        except IntegrityError as error:
            assert error.orig.sqlstate == "23505"
            return "duplicate"

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(lambda _: create(), range(2))) == ["created", "duplicate"]
    with profiles.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT count(*) FROM studio.users WHERE auth_user_id = :id"),
                {"id": auth_id(1)},
            )
            == 1
        )


def test_role_check(profiles):
    with profiles.begin() as connection:
        assert insert(connection, 2)["role"] == "member"
        assert insert(connection, 3, role="coach")["role"] == "coach"
        for role in ("admin", "", "Member", None):
            with pytest.raises(IntegrityError), connection.begin_nested():
                insert(connection, 4, role=role)


def test_incomplete_oauth_profile(profiles):
    with profiles.begin() as connection:
        row = insert(connection, 5)
        assert row["first_name"] is None and row["last_name"] is None
        assert isinstance(row["id"], UUID)
        assert row["is_active"] is True
        assert row["row_version"] == 1
        assert row["created_at"].utcoffset() is not None
        assert row["updated_at"].utcoffset() is not None
        assert insert(connection, 6, first_name="Іван", last_name=None)["last_name"] is None


def test_invalid_locale(profiles):
    with profiles.begin() as connection:
        assert insert(connection, 7, locale="en")["locale"] == "en"
        for locale in ("ru", "UK", "", None):
            with pytest.raises(IntegrityError), connection.begin_nested():
                insert(connection, 8, locale=locale)


def test_fk_and_version_constraints(profiles):
    with profiles.begin() as connection:
        for overrides in (
            {"auth_user_id": auth_id(99)},
            {"auth_user_id": None},
            {"row_version": 0},
            {"row_version": -1},
            {"row_version": None},
        ):
            with pytest.raises(IntegrityError), connection.begin_nested():
                insert(connection, 9, **overrides)


def test_runtime_has_no_profile_access_before_security_card(profiles):
    with profiles.begin() as connection:
        for role in ("studio_web", "studio_worker", "studio_auth_runtime"):
            with connection.begin_nested() as scope:
                connection.exec_driver_sql(f"SET LOCAL ROLE {role}")
                with pytest.raises(ProgrammingError), connection.begin_nested():
                    connection.execute(text("SELECT * FROM studio.users"))
                scope.rollback()


def test_model_matches_head_migrations(profiles):
    from studio.accounts.models import User
    from studio.db import Base, include_migration_name

    assert "auth.users" not in Base.metadata.tables
    with profiles.connect() as connection:
        transaction = connection.begin()
        # Current ORM must match head; other tests retain historical 0002 guarantees.
        command.upgrade(baseline.configuration(connection), "head")
        context = MigrationContext.configure(
            connection,
            opts={
                "include_schemas": True,
                "include_name": include_migration_name,
                "version_table_schema": "studio",
                "compare_server_default": True,
                "include_object": lambda obj, name, kind, reflected, compared: (
                    kind != "table" or name == "users"
                ),
            },
        )
        assert compare_metadata(context, Base.metadata) == []
        with Session(connection) as session, session.begin():
            user = User(auth_user_id=auth_id(10), locale="uk", timezone="Europe/Kyiv")
            session.add(user)
            session.flush()
            assert isinstance(user.id, UUID)
            assert user.role == "member"
            assert user.first_name is None
        transaction.rollback()


def test_failed_command_rolls_back_profile(profiles):
    with pytest.raises(RuntimeError, match="abort"), profiles.begin() as connection:
        insert(connection, 11)
        raise RuntimeError("abort")
    with profiles.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT count(*) FROM studio.users WHERE auth_user_id = :id"),
                {"id": auth_id(11)},
            )
            == 0
        )
