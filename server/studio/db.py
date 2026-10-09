from collections.abc import Iterator, MutableMapping
from contextlib import contextmanager
from typing import Literal

from sqlalchemy import Engine, MetaData, text
from sqlalchemy.orm import DeclarativeBase, Session

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
