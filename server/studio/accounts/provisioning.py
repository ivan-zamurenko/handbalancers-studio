"""Called only after verified upstream identity; never merge by email or accept roles."""

import unicodedata
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from studio.auth.jwt import InvalidIdentity, VerifiedIdentity


def current_profile(session: Session, user_id: UUID) -> dict[str, object]:
    row = (
        session.execute(text("SELECT * FROM studio_private.auth_profile(:id)"), {"id": user_id})
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise InvalidIdentity()
    return dict(row)


def _name(value: object, limit: int) -> str | None:
    if not isinstance(value, str) or len(value) > limit:
        return None
    if any(unicodedata.category(char).startswith("C") for char in value):
        return None
    return " ".join(value.split()) or None


def profile_names(metadata: object) -> dict[str, str | None]:
    # Descriptive user-editable data, never an authority for identity or roles.
    data = metadata if isinstance(metadata, dict) else {}
    first = _name(data.get("given_name"), 100) or _name(data.get("first_name"), 100)
    last = _name(data.get("family_name"), 100) or _name(data.get("last_name"), 100)
    display = _name(data.get("full_name"), 200) or _name(data.get("name"), 200)
    if display is None:
        display = _name(" ".join(part for part in (first, last) if part), 200)
    return {"first": first, "last": last, "display": display}


def provision(
    session: Session, identity: VerifiedIdentity, *, metadata: object = None
) -> dict[str, object]:
    # Caller verifies JWT and upstream user UUID before this transaction.
    # A full name is kept whole, not guessed into first/last name components.
    names = profile_names(metadata)
    user_id = session.scalar(
        text("""SELECT studio_private.provision_oauth_member(
        :auth_id, :first, :last, :display)"""),
        {"auth_id": identity.user_id, **names},
    )
    return current_profile(session, user_id)
