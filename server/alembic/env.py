import os
from urllib.parse import urlparse

from alembic import context
from sqlalchemy import Connection, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool
from studio.accounts.models import User  # noqa: F401
from studio.auth.models import AuthAttempt, WebSession  # noqa: F401
from studio.db import Base, include_migration_name
from studio.migration_connection import migration_owner_username_matches


def migrate(connection: Connection) -> None:
    connection.exec_driver_sql("SET LOCAL lock_timeout = '5s'")
    connection.exec_driver_sql("SET LOCAL statement_timeout = '60s'")
    connection.execute(text("SELECT pg_advisory_xact_lock(190103)"))
    identity = connection.execute(text(
        "SELECT rolname, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
    )).one()
    if identity not in (("migration_owner", False, False), ("postgres", False, True)):
        raise RuntimeError("Migrations require postgres or the dedicated migration_owner, never runtime")
    connection.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS studio")
    owner = connection.scalar(text(
        "SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname = 'studio'"
    ))
    if owner != identity.rolname:
        raise RuntimeError("Existing studio schema has an unexpected owner")
    context.configure(
        connection=connection, target_metadata=Base.metadata,
        include_schemas=True, include_name=include_migration_name,
        version_table_schema="studio",
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    raise RuntimeError("Use an online operator connection for verified transactional migrations")

provided_connection = context.config.attributes.get("connection")
if isinstance(provided_connection, Connection):
    migrate(provided_connection)
else:
    if any(key.startswith("PG") for key in os.environ):
        raise RuntimeError("Libpq environment overrides are not allowed for migrations")
    raw_url = os.environ.get("STUDIO_MIGRATION_DATABASE_URL")
    if not raw_url:
        raise RuntimeError("STUDIO_MIGRATION_DATABASE_URL is required")
    url = make_url(raw_url)
    supabase_host = urlparse(os.environ.get("SUPABASE_URL", "")).hostname
    project_ref = (
        supabase_host.removesuffix(".supabase.co")
        if supabase_host and supabase_host.endswith(".supabase.co")
        else None
    )
    allowed_username = migration_owner_username_matches(url.username, project_ref) or (
        url.username == "postgres" or bool(project_ref) and url.username == f"postgres.{project_ref}"
    )
    if url.drivername != "postgresql+psycopg" or not allowed_username:
        raise RuntimeError("A PostgreSQL psycopg migration administrator URL is required")
    engine = create_engine(
        url, poolclass=NullPool, hide_parameters=True, connect_args={"connect_timeout": 5},
    )
    try:
        with engine.begin() as connection:
            migrate(connection)
    finally:
        engine.dispose()