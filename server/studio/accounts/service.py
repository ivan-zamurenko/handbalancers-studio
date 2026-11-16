"""Own profile and preferences. One command = one studio_web transaction under RLS."""

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from studio.shared.context import Actor

WebTransaction = Callable[[Actor], AbstractContextManager[Session]]
PROFILE_FIELDS = ("first_name", "last_name", "locale", "timezone")


@dataclass(frozen=True)
class RevisionConflict(Exception):
    current: dict[str, object]


def _profile(session: Session) -> dict[str, object]:
    row = (
        session.execute(
            text(
                "SELECT id, first_name, last_name, display_name, role, locale, timezone "
                "FROM studio.users"
            )
        )
        .mappings()
        .one()
    )
    profile = dict(row)
    profile["id"] = str(profile["id"])
    profile["profile_complete"] = bool(profile["first_name"] and profile["last_name"])
    return profile


def get_profile(transaction: WebTransaction, actor: Actor) -> dict[str, object]:
    with transaction(actor) as session:
        return _profile(session)


def update_profile(
    transaction: WebTransaction, actor: Actor, changes: dict[str, str]
) -> dict[str, object]:
    fields = [name for name in PROFILE_FIELDS if name in changes]
    with transaction(actor) as session:
        if fields:
            assignments = ", ".join(f"{name} = :{name}" for name in fields)
            session.execute(
                # studio_web may update only these columns; RLS limits it to the own row.
                text(f"UPDATE studio.users SET {assignments}"),
                {name: changes[name] for name in fields},
            )
        return _profile(session)


def _preferences(session: Session) -> dict[str, object]:
    row = session.execute(
        text("SELECT theme_preference, revision FROM studio.user_preferences")
    ).one_or_none()
    if row is None:
        return {"theme_preference": "auto", "revision": 0}
    return {"theme_preference": row.theme_preference, "revision": row.revision}


def get_preferences(transaction: WebTransaction, actor: Actor) -> dict[str, object]:
    with transaction(actor) as session:
        return _preferences(session)


def update_preferences(
    transaction: WebTransaction, actor: Actor, theme: str, expected_revision: int
) -> dict[str, object]:
    with transaction(actor) as session:
        if expected_revision == 0:
            changed = session.execute(
                text(
                    "INSERT INTO studio.user_preferences (user_id, theme_preference) "
                    "VALUES (:id, :theme) ON CONFLICT (user_id) DO NOTHING RETURNING revision"
                ),
                {"id": actor.user_id, "theme": theme},
            ).scalar_one_or_none()
        else:
            changed = session.execute(
                text(
                    "UPDATE studio.user_preferences SET theme_preference = :theme, "
                    "revision = revision + 1, updated_at = now() WHERE revision = :expected "
                    "RETURNING revision"
                ),
                {"theme": theme, "expected": expected_revision},
            ).scalar_one_or_none()
        current = _preferences(session)
    if changed is None:
        raise RevisionConflict(current)
    return current
