from collections.abc import Callable, Iterator, MutableMapping
from contextlib import AbstractContextManager, contextmanager
from typing import Literal

from sqlalchemy import Engine, MetaData, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session

from studio.settings import Settings
from studio.shared.context import Actor


class Base(DeclarativeBase):
    metadata = MetaData(schema="studio")


def include_migration_name(
    name: str | None,
    type_: Literal[
        "schema",
        "table",
        "column",
        "index",
        "unique_constraint",
        "foreign_key_constraint",
        "check_constraint",
    ],
    parent_names: MutableMapping[
        Literal["schema_name", "table_name", "schema_qualified_table_name"],
        str | None,
    ],
) -> bool:
    if type_ == "schema":
        return name in {"studio", "studio_private"}
    return parent_names.get("schema_name") in {"studio", "studio_private"}


@contextmanager
def command_transaction(engine: Engine, actor: Actor | None) -> Iterator[Session]:
    """One command, one transaction. Authentication must resolve actor beforehand.

    Bind the engine to a non-owner runtime login without BYPASSRLS. This context
    is defense in depth against application mistakes, not a backend sandbox.
    Callers must not commit/rollback early or retain the session beyond the block.
    """
    with Session(engine) as session, session.begin():
        session.execute(
            text("SELECT set_config('studio.user_id', :user_id, true)"),
            {"user_id": str(actor.user_id) if actor is not None else ""},
        )
        yield session


class UnsafeWebRole(RuntimeError):
    pass


# Same guard as the auth runtime: the web login holds studio_web only, never
# owner, superuser, BYPASSRLS or migration privileges (otherwise RLS is moot).
_WEB_ROLE_CHECK = text("""
SELECT NOT r.rolsuper AND NOT r.rolbypassrls AND NOT r.rolcreaterole
    AND pg_has_role(current_user, 'studio_web', 'USAGE')
    AND NOT pg_has_role(current_user, 'studio_auth_runtime', 'MEMBER')
    AND NOT pg_has_role(current_user, 'migration_owner', 'MEMBER')
    AND NOT EXISTS (
        SELECT 1 FROM pg_namespace n
        WHERE n.nspname IN ('studio', 'studio_private')
        AND pg_has_role(current_user, n.nspowner, 'MEMBER'))
FROM pg_roles r WHERE r.rolname = current_user
""")


def web_transaction_factory(
    settings: Settings,
) -> Callable[[Actor], AbstractContextManager[Session]] | None:
    """studio_web login (DATABASE_URL); None keeps /api/me fail-closed (503)."""
    if settings.database_url is None:
        return None
    engine = create_engine(
        settings.database_url.get_secret_value(),
        hide_parameters=True,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=0,
        pool_timeout=5,
        connect_args={"connect_timeout": 5},
    )

    return web_transaction_for(engine)


def web_transaction_for(engine: Engine) -> Callable[[Actor], AbstractContextManager[Session]]:
    @contextmanager
    def transaction(actor: Actor) -> Iterator[Session]:
        with command_transaction(engine, actor) as session:
            if not session.execute(_WEB_ROLE_CHECK).scalar_one():
                raise UnsafeWebRole("DATABASE_URL must be a narrow studio_web login")
            session.execute(text("SET LOCAL statement_timeout='5s'"))
            session.execute(text("SET LOCAL lock_timeout='2s'"))
            yield session

    return transaction
