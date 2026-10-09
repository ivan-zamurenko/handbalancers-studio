import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.pool import NullPool

from server.tests.support.database_guard import require_test_database
from tools import local_stack

ROOT = Path(__file__).resolve().parents[4]


@pytest.fixture(scope="module")
def engine():
    require_test_database()
    container = local_stack.verify_container("test")
    name = "s01_02_probe_" + uuid4().hex
    local_stack.execute_local_sql(container, f"CREATE DATABASE {name};")
    database = None
    try:
        local_stack.execute_local_sql(container, f"""
GRANT CONNECT, CREATE ON DATABASE {name} TO migration_owner;
    \\connect {name}
CREATE SCHEMA auth;
CREATE TABLE auth.users (id uuid PRIMARY KEY);
CREATE SCHEMA storage;
CREATE TABLE storage.objects (id uuid PRIMARY KEY);
CREATE SCHEMA realtime;
CREATE TABLE realtime.messages (id uuid PRIMARY KEY);
""")
        database = create_engine(URL.create(
            "postgresql+psycopg", username="migration_owner",
            password=local_stack.read_migration_password(ROOT / ".local-tools/supabase/test"),
            host="127.0.0.1", port=55322, database=name,
        ), poolclass=NullPool, hide_parameters=True, connect_args={"connect_timeout": 5})
        yield database
    finally:
        if database is not None:
            database.dispose()
        require_test_database()
        assert local_stack.verify_container("test")["Id"] == container["Id"]
        local_stack.execute_local_sql(container, f"DROP DATABASE {name};")


@pytest.fixture
def connection(engine):
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            yield connection
        finally:
            transaction.rollback()


def configuration(connection=None):
    assert (ROOT / "alembic.ini").is_file(), "Alembic baseline entrypoint absent"
    config = Config(str(ROOT / "alembic.ini"))
    if connection is not None:
        config.attributes["connection"] = connection
    return config


def test_upgrade_empty_database(connection):
    assert connection.scalar(text("SELECT to_regnamespace('studio')")) is None
    managed = connection.execute(text("SELECT oid FROM pg_namespace WHERE nspname IN ('auth', 'storage', 'realtime') ORDER BY oid")).all()
    command.upgrade(configuration(connection), "0001")
    command.upgrade(configuration(connection), "0001")
    assert connection.scalar(text("SELECT version_num FROM studio.alembic_version")) == "0001"
    assert connection.execute(text("SELECT nspname, pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname IN ('studio', 'studio_private') ORDER BY nspname")).all() == [("studio", "migration_owner"), ("studio_private", "migration_owner")]
    assert connection.execute(text("SELECT oid FROM pg_namespace WHERE nspname IN ('auth', 'storage', 'realtime') ORDER BY oid")).all() == managed
    assert connection.scalar(text("SELECT count(*) FROM pg_class WHERE relnamespace = 'auth'::regnamespace AND relname = 'users'")) == 1


def test_owner_not_runtime(connection):
    command.upgrade(configuration(connection), "0001")
    assert connection.execute(text(
        "SELECT rolsuper, rolcreatedb, rolcreaterole, rolbypassrls, rolcanlogin "
        "FROM pg_roles WHERE rolname = 'migration_owner'"
    )).one() == (False, False, False, False, True)
    connection.execute(text("CREATE TABLE studio.policy_probe (id integer PRIMARY KEY)"))
    connection.execute(text("INSERT INTO studio.policy_probe VALUES (1)"))
    connection.execute(text("ALTER TABLE studio.policy_probe ENABLE ROW LEVEL SECURITY"))
    connection.execute(text("CREATE FUNCTION studio_private.secret_probe() RETURNS integer LANGUAGE sql AS 'SELECT 1'"))
    expected_schema_usage = {
        "studio_web": (True, False),
        "studio_auth_runtime": (True, True),
        "studio_worker": (True, True),
    }
    for role in ("studio_web", "studio_auth_runtime", "studio_worker"):
        assert connection.execute(text("SELECT rolsuper, rolcreatedb, rolcreaterole, rolbypassrls, rolcanlogin FROM pg_roles WHERE rolname = :role"), {"role": role}).one() == (False, False, False, False, False)
        assert connection.execute(text(
            "SELECT has_schema_privilege(:role, 'studio', 'USAGE'), "
            "has_schema_privilege(:role, 'studio_private', 'USAGE')"
        ), {"role": role}).one() == expected_schema_usage[role]
        assert not connection.scalar(text("SELECT pg_has_role(:role, 'migration_owner', 'MEMBER')"), {"role": role})
        assert not connection.scalar(text("SELECT has_table_privilege(:role, 'studio.policy_probe', 'SELECT')"), {"role": role})
        assert not connection.scalar(text("SELECT has_function_privilege(:role, 'studio_private.secret_probe()', 'EXECUTE')"), {"role": role})
        connection.exec_driver_sql(f"GRANT SELECT ON studio.policy_probe TO {role}")
        with connection.begin_nested() as scope:
            connection.exec_driver_sql(f"SET LOCAL ROLE {role}")
            assert connection.scalar(text("SELECT current_user")) == role
            assert connection.execute(text("SELECT * FROM studio.policy_probe")).all() == []
            with pytest.raises(ProgrammingError), connection.begin_nested():
                connection.execute(text("CREATE TABLE studio.forbidden (id integer)"))
            scope.rollback()
    assert connection.scalar(text("SELECT pg_get_userbyid(relowner) FROM pg_class WHERE oid = 'studio.policy_probe'::regclass")) == "migration_owner"


def test_no_managed_autogenerate(connection):
    command.upgrade(configuration(connection), "0001")
    from studio.db import include_migration_name

    context = MigrationContext.configure(connection, opts={
        "include_schemas": True, "include_name": include_migration_name,
        "version_table_schema": "studio",
    })
    assert compare_metadata(context, MetaData()) == []
    metadata = MetaData()
    for schema in ("studio", "studio_private"):
        Table("new_product_table", metadata, Column("id", Integer, primary_key=True), schema=schema)
    changes = compare_metadata(context, metadata)
    assert {(change[0], change[1].schema) for change in changes} == {("add_table", "studio"), ("add_table", "studio_private")}


def test_upgrade_rolls_back_midway(engine):
    with pytest.raises(RuntimeError, match="abort after DDL"), engine.begin() as connection:
        command.upgrade(configuration(connection), "0001")
        raise RuntimeError("abort after DDL")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT to_regnamespace('studio')")) is None
        assert connection.scalar(text("SELECT to_regnamespace('studio_private')")) is None


def test_downgrade_requires_forward_repair(connection):
    command.upgrade(configuration(connection), "0001")
    with pytest.raises(RuntimeError, match="forward repair"):
        command.downgrade(configuration(connection), "base")
    assert connection.scalar(text("SELECT version_num FROM studio.alembic_version")) == "0001"


def test_concurrent_upgrade_serializes(engine):
    def upgrade():
        environment = {
            "STUDIO_MIGRATION_DATABASE_URL": engine.url.render_as_string(hide_password=False)
        }
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "-c", str(ROOT / "alembic.ini"), "upgrade", "0001"],
            cwd=ROOT, env=environment, capture_output=True, text=True, check=False, timeout=120,
        )
        assert result.returncode == 0, "Concurrent Alembic command failed"

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(lambda _: upgrade(), range(2)))
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM studio.alembic_version")) == 1