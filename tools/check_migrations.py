"""Guarded migration gate. --fresh refuses existing product schemas; never resets."""

import argparse
import subprocess
import sys
from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Connection, create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool
from studio.accounts.models import User  # noqa: F401
from studio.auth.models import AuthAttempt, WebSession  # noqa: F401
from studio.db import Base, include_migration_name

from server.tests.support.database_guard import require_test_database
from tools import local_stack

ROOT = Path(__file__).resolve().parents[1]
DB_SUITES = (
    "server/tests/integration/database",
    "server/tests/integration/onboarding",
    "server/tests/integration/billing",
    "server/tests/security/database",
    "server/tests/security/accounts",
    "server/tests/integration/auth",
)


class MigrationCheckError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise MigrationCheckError(message)


def single_head(directory: Path) -> str:
    scripts = ScriptDirectory(str(directory))
    heads = scripts.get_heads()
    require(
        len(heads) == 1 and len(scripts.get_bases()) == 1, "Expected one migration head and base"
    )
    require(
        all(
            not revision.is_branch_point and not revision.is_merge_point
            for revision in scripts.walk_revisions()
        ),
        "Migrations must form one linear chain",
    )
    return heads[0]


def managed_fingerprint(connection: Connection) -> tuple:
    # Excludes incoming internal FK triggers created by product references.
    # Includes definitions, not just object counts or OIDs.
    queries = (
        """SELECT nspname, nspowner, nspacl::text FROM pg_namespace
           WHERE nspname IN ('auth','storage','realtime') ORDER BY nspname""",
        """SELECT n.nspname,c.relname,c.relkind,c.relowner,c.relacl::text,c.relrowsecurity,c.relforcerowsecurity
           FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
           WHERE n.nspname IN ('auth','storage','realtime') ORDER BY 1,2""",
        """SELECT n.nspname,c.relname,a.attnum,a.attname,format_type(a.atttypid,a.atttypmod),
                  a.attnotnull,a.attidentity,a.attgenerated,a.attacl::text,pg_get_expr(d.adbin,d.adrelid)
           FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
           JOIN pg_namespace n ON n.oid=c.relnamespace
           LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum
           WHERE n.nspname IN ('auth','storage','realtime') AND a.attnum>0 AND NOT a.attisdropped
           ORDER BY 1,2,3""",
        """SELECT n.nspname,c.conname,pg_get_constraintdef(c.oid)
           FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace
           WHERE n.nspname IN ('auth','storage','realtime') ORDER BY 1,2,3""",
        """SELECT schemaname,tablename,indexname,indexdef FROM pg_indexes
           WHERE schemaname IN ('auth','storage','realtime') ORDER BY 1,2,3""",
        """SELECT n.nspname,p.oid::regprocedure::text,p.proowner,p.proacl::text,pg_get_functiondef(p.oid)
           FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
           WHERE n.nspname IN ('auth','storage','realtime') AND p.prokind IN ('f','p') ORDER BY 1,2""",
        """SELECT schemaname,tablename,policyname,roles::text,cmd,qual,with_check FROM pg_policies
           WHERE schemaname IN ('auth','storage','realtime') ORDER BY 1,2,3""",
        """SELECT n.nspname,c.relname,t.tgname,pg_get_triggerdef(t.oid)
           FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
           JOIN pg_namespace n ON n.oid=c.relnamespace
           WHERE n.nspname IN ('auth','storage','realtime') AND NOT t.tgisinternal ORDER BY 1,2,3""",
    )
    return tuple(tuple(tuple(row) for row in connection.execute(text(query))) for query in queries)


def verify_isolation(connection: Connection, *, owner: str = "migration_owner") -> None:
    tables = ["studio.users", "studio_private.web_sessions", "studio_private.auth_attempts"]
    # Later tables are checked once present (adopted 0006 baseline predates them).
    for later in (
        "studio_private.audit_events",
        "studio.user_preferences",
        "studio.onboarding_profiles",
        "studio.billing_customers",
        "studio.subscriptions",
        "studio.checkout_attempts",
        "studio.trial_claims",
        "studio_private.webhook_events",
    ):
        if connection.scalar(text("SELECT to_regclass(:t)"), {"t": later}) is not None:
            tables.append(later)
    for table in tables:
        require(
            connection.execute(
                text(
                    "SELECT pg_get_userbyid(relowner),relrowsecurity FROM pg_class WHERE oid=to_regclass(:table)"
                ),
                {"table": table},
            ).one()
            == (owner, True),
            "Product ownership/RLS mismatch",
        )
        for role in ("anon", "authenticated", "studio_worker"):
            billing_grants = {
                "studio.billing_customers": {"SELECT", "INSERT"},
                "studio.subscriptions": {"SELECT", "INSERT", "UPDATE"},
                "studio.checkout_attempts": {"SELECT", "INSERT", "UPDATE"},
                "studio.trial_claims": {"SELECT", "INSERT", "UPDATE"},
                "studio_private.webhook_events": {"SELECT", "INSERT", "UPDATE"},
            }
            if (
                role == "studio_worker"
                and table in billing_grants
                and connection.scalar(text("SELECT to_regclass('studio.checkout_attempts')"))
            ):
                for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE"):
                    require(
                        bool(
                            connection.scalar(
                                text("SELECT has_table_privilege(:r,:t,:p)"),
                                {"r": role, "t": table, "p": privilege},
                            )
                        )
                        == (privilege in billing_grants[table]),
                        "Unexpected billing worker grant",
                    )
                continue
            require(
                not connection.scalar(
                    text(
                        "SELECT has_table_privilege(:role,:table,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE')"
                    ),
                    {"role": role, "table": table},
                ),
                "Unexpected runtime table grant",
            )
    for column in ("id", "auth_user_id", "role", "is_active", "created_at", "row_version"):
        require(
            not connection.scalar(
                text("SELECT has_column_privilege('studio_web','studio.users',:column,'UPDATE')"),
                {"column": column},
            ),
            "Protected profile column is mutable",
        )
    for table in ("studio_private.web_sessions", "studio_private.auth_attempts"):
        require(
            not connection.scalar(
                text("SELECT has_table_privilege('studio_web',:table,'SELECT')"), {"table": table}
            ),
            "Web role can read private tokens",
        )
    for role in ("studio_web", "studio_auth_runtime", "studio_worker"):
        require(
            connection.execute(
                text("SELECT rolsuper,rolbypassrls,rolcanlogin FROM pg_roles WHERE rolname=:role"),
                {"role": role},
            ).one()
            == (False, False, False),
            "Runtime role exceeds expected privileges",
        )


def verify_fresh_database() -> None:
    # Do not accept an operator URL from environment or command-line arguments.
    require_test_database()
    head = single_head(ROOT / "server/alembic")
    engine = create_engine(
        URL.create(
            "postgresql+psycopg",
            username="migration_owner",
            password=local_stack.read_migration_password(ROOT / ".local-tools/supabase/test"),
            host="127.0.0.1",
            port=55322,
            database="postgres",
        ),
        poolclass=NullPool,
        hide_parameters=True,
        connect_args={"connect_timeout": 5},
    )
    try:
        with engine.begin() as connection:
            require(
                connection.scalar(text("SELECT to_regclass('auth.users')")) is not None,
                "Managed auth.users must already exist",
            )
            require(
                connection.execute(
                    text(
                        "SELECT nspname FROM pg_namespace WHERE nspname IN ('studio','studio_private')"
                    )
                ).first()
                is None,
                "Fresh migration check requires absent product schemas; no reset performed",
            )
            before = managed_fingerprint(connection)
            config = Config(str(ROOT / "alembic.ini"))
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            command.upgrade(config, "head")
            require(
                connection.scalar(text("SELECT version_num FROM studio.alembic_version")) == head,
                "Upgrade did not reach the single head",
            )
            require(
                before == managed_fingerprint(connection), "Managed schema changed during upgrade"
            )
            context = MigrationContext.configure(
                connection,
                opts={
                    "include_schemas": True,
                    "include_name": include_migration_name,
                    "version_table_schema": "studio",
                    "compare_server_default": True,
                },
            )
            require(
                compare_metadata(context, Base.metadata) == [], "ORM metadata differs from database"
            )
            verify_isolation(connection)
        print(
            "Fresh managed-Supabase upgrade/repeat, metadata and privilege checks passed.",
            flush=True,
        )
    finally:
        engine.dispose()


def pytest_sessionfinish(session, exitstatus):
    """A skipped/xfail DB guarantee is not a passing gate."""
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter and any(reporter.stats.get(kind) for kind in ("skipped", "xfailed", "xpassed")):
        session.exitstatus = 1


def run_guarded(*, fresh: bool = False, root: Path = ROOT) -> int:
    for suite in DB_SUITES:
        require(any((root / suite).rglob("test_*.py")), "Required DB test suite is missing")
    require_test_database()
    if fresh:
        verify_fresh_database()
    for suite in DB_SUITES:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-p", "tools.check_migrations", suite, "-q"],
            cwd=root,
            check=False,
            timeout=600,
        )
        if result.returncode:
            return result.returncode
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fresh", action="store_true", help="Require blank product schemas before upgrade"
    )
    parser.add_argument("--guarded", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--heads-only", action="store_true")
    args = parser.parse_args()
    try:
        head = single_head(ROOT / "server/alembic")
        print(f"Single migration head: {head}", flush=True)
        if args.heads_only:
            return 0
        if args.guarded:
            return run_guarded(fresh=args.fresh)
        return local_stack.run_tests(
            [
                sys.executable,
                "-m",
                "tools.check_migrations",
                "--guarded",
                *(["--fresh"] if args.fresh else []),
            ]
        )
    except (MigrationCheckError, local_stack.UnsafeDatabaseTarget) as error:
        print(str(error), file=sys.stderr)
        return 1
    except (SQLAlchemyError, OSError, subprocess.SubprocessError):
        print("Migration check failed; infrastructure details withheld.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
