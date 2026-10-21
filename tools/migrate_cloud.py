"""Verified migrations for the owner-approved existing Supabase project."""

import argparse
import getpass
import os
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

from tools.check_migrations import (
    ROOT,
    MigrationCheckError,
    managed_fingerprint,
    require,
    single_head,
    verify_isolation,
)

PROJECT_REF = "dwckvtuhgelhsbjyhpks"
POOLER_HOST = "aws-1-eu-west-1.pooler.supabase.com"
TARGET_REVISION = "0006"


def upgrade_verified(connection: Connection, *, adopt_bootstrap: bool = False) -> str:
    require(connection.in_transaction(), "An enclosing transaction is required")
    require(single_head(ROOT / "server/alembic") == TARGET_REVISION, "Unapproved migration head")
    connection.exec_driver_sql("SET LOCAL lock_timeout = '5s'")
    connection.exec_driver_sql("SET LOCAL statement_timeout = '60s'")
    connection.execute(text("SELECT pg_advisory_xact_lock(190103)"))
    managed_before = managed_fingerprint(connection)
    config = Config(str(ROOT / "alembic.ini"))
    config.attributes["connection"] = connection
    if adopt_bootstrap:
        from tools.registration_baseline import (
            reconcile_default_privileges,
            verify_registration_baseline,
        )

        require(connection.scalar(text("SELECT current_user")) == "postgres",
                "Bootstrap adoption requires the schema owner postgres")
        verify_registration_baseline(connection)
        version_table = connection.scalar(text("SELECT to_regclass('studio.alembic_version')"))
        if version_table is not None:
            require(connection.execute(text(
                "SELECT version_num FROM studio.alembic_version"
            )).all() == [(TARGET_REVISION,)], "Unexpected existing revision; refusing adoption")
        reconcile_default_privileges(connection)
        # Verified adoption records equivalence; it does not replay historical DDL.
        if version_table is None:
            command.stamp(config, TARGET_REVISION)
        connection.exec_driver_sql(
            "REVOKE ALL ON studio.alembic_version FROM PUBLIC,anon,authenticated,"
            "studio_web,studio_auth_runtime,studio_worker"
        )
        connection.exec_driver_sql("ALTER TABLE studio.alembic_version ENABLE ROW LEVEL SECURITY")
        verify_registration_baseline(connection)
    else:
        command.upgrade(config, TARGET_REVISION)
    require(
        connection.scalar(text("SELECT version_num FROM studio.alembic_version"))
        == TARGET_REVISION,
        "Unexpected Alembic revision",
    )
    verify_isolation(connection, owner="postgres")
    require(
        connection.execute(text(
            "SELECT convalidated, confrelid = 'auth.users'::regclass "
            "FROM pg_constraint WHERE conrelid='studio.users'::regclass "
            "AND conname='fk_users_auth_user_id' AND contype='f'"
        )).one() == (True, True),
        "Auth foreign key missing or unvalidated",
    )
    require(managed_fingerprint(connection) == managed_before, "Managed schema changed")
    return TARGET_REVISION


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Commit verified migrations; otherwise roll back")
    parser.add_argument("--adopt-bootstrap", action="store_true",
                        help="Verify and adopt existing registration tables as baseline 0006")
    parser.add_argument("--ssl-root-cert", default="system", help="Trusted CA file from Supabase Dashboard, or system")
    arguments = parser.parse_args()
    if any(key.startswith("PG") for key in os.environ):
        parser.error("Libpq environment overrides are not allowed")
    if not sys.stdin.isatty():
        parser.error("Run in a local interactive terminal for hidden password entry")
    password = getpass.getpass(f"Postgres password for {PROJECT_REF} (hidden): ")
    if not password:
        parser.error("A nonempty operator password is required")
    engine = create_engine(
        URL.create(
            "postgresql+psycopg", username=f"postgres.{PROJECT_REF}", password=password,
            host=POOLER_HOST, port=5432, database="postgres",
            query={"sslmode": "verify-full", "sslrootcert": arguments.ssl_root_cert},
        ),
        poolclass=NullPool, hide_parameters=True, connect_args={"connect_timeout": 10},
    )
    del password
    try:
        with engine.begin() as connection:
            upgrade_verified(connection, adopt_bootstrap=arguments.adopt_bootstrap)
            if not arguments.apply:
                connection.rollback()
        outcome = "Applied" if arguments.apply else "Checked and rolled back"
        operation = "baseline adoption" if arguments.adopt_bootstrap else "migration upgrade"
        print(f"{outcome} {operation} to Alembic {TARGET_REVISION}; ownership and RLS verified.", flush=True)
        return 0
    except (SQLAlchemyError, MigrationCheckError, RuntimeError) as error:
        sqlstate = getattr(getattr(error, "orig", None), "sqlstate", None) or "unavailable"
        print(
            f"Migration failed ({type(error).__name__}, SQLSTATE {sqlstate}); "
            "uncommitted changes rolled back. No credentials logged.", flush=True,
        )
        if isinstance(error, MigrationCheckError):
            print(str(error), flush=True)  # Only our fixed diagnostics, never SQL/parameters.
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
