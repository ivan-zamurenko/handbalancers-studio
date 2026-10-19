"""Called only after verified upstream identity; never merge by email or accept roles."""

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


def provision(session: Session, identity: VerifiedIdentity) -> dict[str, object]:
    # OAuth names may be absent (notably Apple). Leave profile incomplete instead
    # of deriving identity from email or allowing metadata to assign a role.
    user_id = session.scalar(
        text("""SELECT studio_private.provision_member(
        :auth_id, NULL, NULL, 'uk', 'UTC')"""),
        {"auth_id": identity.user_id},
    )
    return current_profile(session, user_id)
