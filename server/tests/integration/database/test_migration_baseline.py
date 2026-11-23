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
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, event, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
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


@pytest.fixture(scope="module")
def operator_engine(engine):
    require_test_database()
    container = local_stack.verify_container("test")
    environment = dict(item.split("=", 1) for item in container["Config"]["Env"] if "=" in item)
    operator = create_engine(
        engine.url.set(username="postgres", password=environment["POSTGRES_PASSWORD"]),
        poolclass=NullPool, hide_parameters=True, connect_args={"connect_timeout": 5},
    )
    try:
        local_stack.execute_local_sql(container, f"""
GRANT CONNECT, CREATE ON DATABASE {engine.url.database} TO postgres;
\\connect {engine.url.database}
GRANT USAGE ON SCHEMA auth TO postgres;
GRANT REFERENCES (id) ON auth.users TO postgres;
""")
        yield operator
    finally:
        operator.dispose()


def operator_membership(connection):
    return connection.execute(text(
        "SELECT grantor, admin_option, inherit_option, set_option FROM pg_auth_members "
        "WHERE roleid='migration_owner'::regrole AND member='postgres'::regrole ORDER BY grantor"
    )).all()


def test_operator_fk_upgrade_repeat_preserves_privileges(operator_engine):
    ddl_roles = []

    def record_ddl(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().split(None, 1)[0].upper() in {"CREATE", "ALTER", "DROP"}:
            with connection.connection.cursor() as identity_cursor:
                identity_cursor.execute("SELECT current_user")
                ddl_roles.append((statement, identity_cursor.fetchone()[0]))

    with operator_engine.connect() as connection, connection.begin() as transaction:
        before = operator_membership(connection)
        assert connection.execute(text(
            "SELECT has_schema_privilege('migration_owner','auth','USAGE'), "
            "has_column_privilege('migration_owner','auth.users','id','REFERENCES')"
        )).one() == (False, False)
        event.listen(connection, "before_cursor_execute", record_ddl)
        command.upgrade(configuration(connection), "head")
        command.upgrade(configuration(connection), "head")
        assert connection.scalar(text("SELECT current_user")) == "postgres"
        assert operator_membership(connection) == before
        assert connection.scalar(text("SELECT version_num FROM studio.alembic_version")) == "0016"
        assert connection.execute(text(
            "SELECT DISTINCT pg_get_userbyid(relowner) FROM pg_class "
            "WHERE relnamespace IN ('studio'::regnamespace,'studio_private'::regnamespace)"
        )).all() == [("postgres",)]
        assert connection.execute(text(
            "SELECT has_schema_privilege('migration_owner','auth','USAGE'), "
            "has_column_privilege('migration_owner','auth.users','id','REFERENCES')"
        )).one() == (False, False)
        assert ddl_roles
        assert all(role == "postgres" for _, role in ddl_roles)
        with (
            pytest.raises(IntegrityError) as violation,
            connection.begin_nested(),
        ):
            connection.execute(text(
                "INSERT INTO studio.users (auth_user_id,locale,timezone) "
                "VALUES (:identifier,'uk','UTC')"
            ), {"identifier": uuid4()})
        assert violation.value.orig.sqlstate == "23503"
        assert not connection.scalar(text(
            "SELECT has_schema_privilege('studio_auth_runtime','studio','CREATE')"
        ))
        assert not connection.scalar(text(
            "SELECT has_column_privilege('studio_web','studio.users','role','UPDATE')"
        ))
        transaction.rollback()


def test_operator_upgrade_failure_rolls_back_roles_and_ddl(operator_engine):
    with operator_engine.connect() as connection:
        before = operator_membership(connection)
        connection.rollback()
        with pytest.raises(RuntimeError, match="abort after operator upgrade"), connection.begin():
            command.upgrade(configuration(connection), "head")
            raise RuntimeError("abort after operator upgrade")
        assert connection.scalar(text("SELECT current_user")) == "postgres"
        assert operator_membership(connection) == before
        assert connection.scalar(text("SELECT to_regnamespace('studio')")) is None
        assert connection.scalar(text("SELECT to_regnamespace('studio_private')")) is None


def test_runtime_cannot_run_migrations(connection):
    connection.exec_driver_sql("SET LOCAL ROLE studio_auth_runtime")
    with pytest.raises(RuntimeError, match="Migrations require"):
        command.upgrade(configuration(connection), "0001")
    assert connection.scalar(text("SELECT to_regnamespace('studio')")) is None


def test_verified_cloud_upgrade_preserves_managed_schemas(operator_engine):
    from tools.migrate_cloud import upgrade_verified

    with operator_engine.connect() as connection, connection.begin() as transaction:
        before = operator_membership(connection)
        command.upgrade(configuration(connection), "0009")
        assert connection.scalar(text("SELECT to_regclass('studio.onboarding_profiles')")) is None
        # Owner approved the questionnaire migration 0010 on 2026-11-18.
        assert upgrade_verified(connection) == "0010"
        assert upgrade_verified(connection) == "0010"  # A second run is a verified no-op.
        assert connection.scalar(text(
            "SELECT has_column_privilege('studio_auth_runtime', "
            "'studio_private.web_sessions', 'encrypted_tokens', 'UPDATE')"
        ))
        for table in ("studio_private.audit_events", "studio.user_preferences", "studio.onboarding_profiles"):
            assert connection.scalar(text("SELECT relrowsecurity FROM pg_class WHERE oid=to_regclass(:t)"), {"t": table})
        assert operator_membership(connection) == before
        assert connection.scalar(text("SELECT current_user")) == "postgres"
        transaction.rollback()


@pytest.mark.parametrize("drift", [
    "DROP TABLE studio.onboarding_profiles",
    "ALTER POLICY onboarding_select_own ON studio.onboarding_profiles USING (true)",
    "GRANT UPDATE(user_id) ON studio.onboarding_profiles TO studio_web",
    "GRANT SELECT ON studio.onboarding_profiles TO studio_auth_runtime",
    "ALTER FUNCTION studio.has_distinct_elements(anyarray) SECURITY DEFINER",
    "GRANT EXECUTE ON FUNCTION studio.has_distinct_elements(anyarray) TO PUBLIC",
])
def test_cloud_onboarding_drift_is_rejected(operator_engine, monkeypatch, drift):
    from tools import migrate_cloud
    from tools.check_migrations import MigrationCheckError

    monkeypatch.setattr(migrate_cloud, "APPROVED_CLOUD_REVISION", "0010")
    with operator_engine.connect() as connection, connection.begin() as transaction:
        command.upgrade(configuration(connection), "0010")
        connection.exec_driver_sql(drift)
        with pytest.raises(MigrationCheckError, match="Onboarding"):
            migrate_cloud.upgrade_verified(connection)
        transaction.rollback()


def bootstrap_registration(connection):
    sql = (ROOT / "supabase/bootstrap-registration.sql").read_text()
    # Keep the real bootstrap DDL inside the test's rollback-only transaction.
    connection.exec_driver_sql(sql.split("BEGIN;", 1)[1].rsplit("COMMIT;", 1)[0])


def test_adopt_populated_registration_bootstrap(operator_engine):
    from tools.migrate_cloud import upgrade_verified

    identity_id = uuid4()
    container = local_stack.verify_container("test")
    local_stack.execute_local_sql(container, f"""
\\connect {operator_engine.url.database}
INSERT INTO auth.users (id) VALUES ('{identity_id}');
""")
    with operator_engine.connect() as connection, connection.begin():
        bootstrap_registration(connection)
        user_id = connection.scalar(text("""
            INSERT INTO studio.users(auth_user_id,first_name,locale,timezone)
            VALUES (:identity,'Migration test','uk','UTC') RETURNING id
        """), {"identity": identity_id})
        connection.execute(text("""
            INSERT INTO studio_private.web_sessions
              (id,session_key_hash,user_id,upstream_session_id,encrypted_tokens,
               access_expires_at,expires_at)
            VALUES (:id,:hash,:user,:upstream,'synthetic-ciphertext',now(),now()+interval '1 day')
        """), {"id": uuid4(), "hash": "b" * 64, "user": user_id, "upstream": uuid4()})
        connection.execute(text("""
            INSERT INTO studio_private.auth_attempts
              (id,state_hash,user_id,provider,encrypted_verifier,nonce_hash,
               allowed_return_path,expires_at)
            VALUES (:id,:hash,:user,'google','synthetic-verifier',:hash,'/plans',now())
        """), {"id": uuid4(), "hash": "c" * 64, "user": user_id})
        connection.execute(text("""
            INSERT INTO studio_private.auth_rate_limits
            VALUES (:bucket, now(), 2)
        """), {"bucket": "a" * 64})
        tables = ("studio.users", "studio_private.web_sessions",
                  "studio_private.auth_attempts", "studio_private.auth_rate_limits")
        before = {table: connection.execute(text(f"SELECT * FROM {table}")).all()
                  for table in tables}
        assert upgrade_verified(connection, adopt_bootstrap=True) == "0006"
        assert upgrade_verified(connection, adopt_bootstrap=True) == "0006"
        assert {table: connection.execute(text(f"SELECT * FROM {table}")).all()
                for table in tables} == before
        assert connection.scalar(text("SELECT version_num FROM studio.alembic_version")) == "0006"
        # The adopted cloud baseline then upgrades to the approved revision, data intact.
        assert upgrade_verified(connection) == "0010"
        assert {table: connection.execute(text(f"SELECT * FROM {table}")).all()
                for table in tables} == before
        connection.exec_driver_sql("CREATE FUNCTION studio_private.future_fn() RETURNS int "
                                   "LANGUAGE sql AS 'SELECT 1'")
        connection.exec_driver_sql("CREATE TYPE studio_private.future_type AS ENUM ('test')")
        assert not connection.scalar(text(
            "SELECT has_function_privilege('anon','studio_private.future_fn()','EXECUTE')"
        ))
        assert not connection.scalar(text(
            "SELECT has_type_privilege('anon','studio_private.future_type','USAGE')"
        ))
        connection.rollback()


def test_baseline_manifest_matches_real_migrations_and_bootstrap(operator_engine):
    from tools.registration_baseline import verify_registration_baseline

    with operator_engine.connect() as connection:
        with connection.begin():
            command.upgrade(configuration(connection), "0006")
            verify_registration_baseline(connection)
            connection.rollback()
        with connection.begin():
            bootstrap_registration(connection)
            verify_registration_baseline(connection)
            connection.rollback()


@pytest.mark.parametrize("drift", [
    "ALTER TABLE studio.users ADD COLUMN unexpected text",
    "ALTER TABLE studio.users DISABLE ROW LEVEL SECURITY",
    "ALTER TABLE studio.users DROP CONSTRAINT fk_users_auth_user_id",
    "ALTER POLICY users_select_own ON studio.users USING (true)",
    "GRANT SELECT ON studio_private.web_sessions TO anon",
    "GRANT UPDATE(encrypted_tokens) ON studio_private.web_sessions TO studio_auth_runtime",
    "ALTER FUNCTION studio_private.auth_profile(uuid) SECURITY INVOKER",
    ("CREATE OR REPLACE FUNCTION studio_private.auth_profile(p_user_id uuid) "
    "RETURNS TABLE(id uuid,auth_user_id uuid,first_name text,last_name text,role text,"
    "locale text,timezone text,display_name text) LANGUAGE sql STABLE SECURITY DEFINER "
    "SET search_path=pg_catalog,pg_temp AS 'SELECT id,auth_user_id,first_name,last_name,"
    "role,locale,timezone,display_name FROM studio.users'"),
])
def test_adoption_rejects_drift_before_creating_history(operator_engine, drift):
    from tools.check_migrations import MigrationCheckError
    from tools.migrate_cloud import upgrade_verified

    with operator_engine.connect() as connection, connection.begin():
        bootstrap_registration(connection)
        connection.exec_driver_sql(drift)
        with pytest.raises(MigrationCheckError, match="baseline differs"):
            upgrade_verified(connection, adopt_bootstrap=True)
        assert connection.scalar(text("SELECT to_regclass('studio.alembic_version')")) is None
        connection.rollback()


def test_adoption_rollback_preserves_bootstrap(operator_engine, monkeypatch):
    from tools.migrate_cloud import upgrade_verified
    from tools.registration_baseline import catalogue_fingerprints

    stamp = command.stamp

    def fail_after_stamp(*args, **kwargs):
        stamp(*args, **kwargs)
        raise RuntimeError("injected failure after adoption")

    with operator_engine.connect() as connection, connection.begin():
        bootstrap_registration(connection)
        before = catalogue_fingerprints(connection)
        defaults = connection.execute(text("SELECT * FROM pg_default_acl ORDER BY oid")).all()
        monkeypatch.setattr(command, "stamp", fail_after_stamp)
        with pytest.raises(RuntimeError, match="injected failure"), connection.begin_nested():
            upgrade_verified(connection, adopt_bootstrap=True)
        assert catalogue_fingerprints(connection) == before
        assert connection.scalar(text("SELECT to_regclass('studio.alembic_version')")) is None
        assert connection.execute(text("SELECT * FROM pg_default_acl ORDER BY oid")).all() == defaults
        connection.rollback()


def test_adoption_rejects_unknown_revision(operator_engine):
    from tools.check_migrations import MigrationCheckError
    from tools.migrate_cloud import upgrade_verified

    with operator_engine.connect() as connection, connection.begin():
        command.upgrade(configuration(connection), "0006")
        connection.exec_driver_sql("UPDATE studio.alembic_version SET version_num='9999'")
        with pytest.raises(MigrationCheckError, match="Unexpected existing revision"):
            upgrade_verified(connection, adopt_bootstrap=True)
        assert connection.scalar(text("SELECT version_num FROM studio.alembic_version")) == "9999"
        connection.rollback()


def test_adoption_protects_history_from_inherited_default_grants(operator_engine):
    from tools.migrate_cloud import upgrade_verified

    with operator_engine.connect() as connection, connection.begin():
        bootstrap_registration(connection)
        connection.exec_driver_sql(
            "ALTER DEFAULT PRIVILEGES GRANT ALL ON TABLES TO anon,authenticated,studio_auth_runtime"
        )
        upgrade_verified(connection, adopt_bootstrap=True)
        for role in ("anon", "authenticated", "studio_auth_runtime"):
            assert not connection.scalar(text(
                "SELECT has_table_privilege(:role,'studio.alembic_version',"
                "'SELECT,INSERT,UPDATE,DELETE,TRUNCATE')"
            ), {"role": role})
        assert connection.scalar(text(
            "SELECT relrowsecurity FROM pg_class WHERE oid='studio.alembic_version'::regclass"
        ))
        connection.rollback()


def test_adoption_waits_on_existing_migration_lock_with_timeout(operator_engine):
    from tools.migrate_cloud import upgrade_verified

    with operator_engine.connect() as holder, holder.begin():
        holder.execute(text("SELECT pg_advisory_xact_lock(190103)"))
        with operator_engine.connect() as waiter:
            with pytest.raises(OperationalError) as blocked, waiter.begin():
                upgrade_verified(waiter, adopt_bootstrap=True)
            assert blocked.value.orig.sqlstate == "55P03"
            assert waiter.scalar(text("SELECT to_regclass('studio.alembic_version')")) is None


def test_runtime_cannot_adopt_bootstrap(connection):
    from tools.check_migrations import MigrationCheckError
    from tools.migrate_cloud import upgrade_verified

    # The existing migration_owner fixture can SET ROLE; postgres deliberately cannot.
    connection.exec_driver_sql("SET LOCAL ROLE studio_auth_runtime")
    with pytest.raises(MigrationCheckError, match="requires the schema owner"):
        upgrade_verified(connection, adopt_bootstrap=True)
    assert connection.scalar(text("SELECT to_regnamespace('studio')")) is None


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
        arguments = [sys.executable, "-m", "alembic", "-c", str(ROOT / "alembic.ini"), "upgrade", "0001"]
        result = subprocess.run(
            arguments,
            cwd=ROOT, env=environment, capture_output=True, text=True, check=False, timeout=120,
        )
        assert result.returncode == 0, "Concurrent Alembic command failed"

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(lambda _: upgrade(), range(2)))
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM studio.alembic_version")) == 1
        assert connection.scalar(text("SELECT version_num FROM studio.alembic_version")) == "0001"
