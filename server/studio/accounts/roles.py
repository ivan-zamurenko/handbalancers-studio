"""Operator-only role changes. Runs on the migration-owner connection, never on HTTP."""

from uuid import UUID

from sqlalchemy import Connection, text


class RoleChangeRejected(Exception):
    pass


def _set_role(conn: Connection, auth_user_id: UUID, role: str, *, actor: str, action: str) -> bool:
    # A profile exists only after verified upstream identity (provisioning), so a
    # missing/inactive profile means an unverified or unknown identity.
    row = conn.execute(
        text(
            "SELECT id, role FROM studio.users WHERE auth_user_id = :auth AND is_active FOR UPDATE"
        ),
        {"auth": auth_user_id},
    ).one_or_none()
    if row is None:
        raise RoleChangeRejected("No active verified profile for this auth user id")
    if row.role == role:
        return False
    conn.execute(
        text(
            "UPDATE studio.users SET role = :role, updated_at = now(), "
            "row_version = row_version + 1 WHERE id = :id"
        ),
        {"role": role, "id": row.id},
    )
    conn.execute(
        text(
            "INSERT INTO studio_private.audit_events (actor_type, actor, action, subject_user_id) "
            "VALUES ('human', :actor, :action, :id)"
        ),
        {"actor": actor, "action": action, "id": row.id},
    )
    return True


def grant_coach(conn: Connection, auth_user_id: UUID, *, actor: str) -> bool:
    return _set_role(conn, auth_user_id, "coach", actor=actor, action="grant_coach")


def revoke_coach(conn: Connection, auth_user_id: UUID, *, actor: str) -> bool:
    return _set_role(conn, auth_user_id, "member", actor=actor, action="revoke_coach")
