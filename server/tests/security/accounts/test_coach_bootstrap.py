"""S04-05: coach role only via operator CLI on a verified profile, with audit."""

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import text

from server.tests.integration.auth import test_oauth_flow as flow_support
from server.tests.integration.database.test_auth_storage import (  # noqa: F401
    database_engine,
    storage_db,
)

flow = flow_support.flow


def signed_in(service):
    start = service.start("google", "/plans")
    result = asyncio.run(
        service.finish("google", start.attempt, start.binding.get_secret_value(), "code")
    )
    return result.cookie.get_secret_value()


def role_of(service, cookie):
    return asyncio.run(service.session_profile(cookie))["role"]


def audit(db, auth_id):
    with db.connect() as conn:
        return conn.execute(
            text(
                "SELECT a.action, a.actor_type, a.actor FROM studio_private.audit_events a "
                "JOIN studio.users u ON u.id = a.subject_user_id WHERE u.auth_user_id=:a "
                "ORDER BY a.occurred_at"
            ),
            {"a": auth_id},
        ).all()


def test_member_cannot_promote(flow):
    from studio.main import create_app

    _, _, db, _ = flow
    with db.connect() as conn:
        for role in ("studio_web", "studio_auth_runtime", "anon", "authenticated"):
            assert not conn.scalar(
                text("SELECT has_column_privilege(:r, 'studio.users', 'role', 'UPDATE')"),
                {"r": role},
            )
            assert not conn.scalar(
                text(
                    "SELECT has_table_privilege(:r, 'studio_private.audit_events', "
                    "'SELECT,INSERT,UPDATE,DELETE')"
                ),
                {"r": role},
            )
    paths = list(create_app({"app_env": "test"}).openapi()["paths"])
    assert paths
    assert not [p for p in paths if "role" in p or "coach" in p or "admin" in p]


def test_verified_owner_only(flow):
    from studio.accounts import cli, roles

    _, _, db, _ = flow
    missing = uuid4()
    with db.begin() as conn, pytest.raises(roles.RoleChangeRejected):
        roles.grant_coach(conn, missing, actor="owner")
    assert audit(db, missing) == []
    # Operator must name the verified auth UUID; an email is not an identity.
    assert cli.main(["grant-coach", "owner@example.test", "--actor", "owner"]) == 2


def test_repeat_bootstrap_no_duplicate(flow):
    from studio.accounts import roles

    service, _, db, auth_id = flow
    cookie = signed_in(service)
    for _ in range(2):
        with db.begin() as conn:
            roles.grant_coach(conn, auth_id, actor="owner")
    with db.connect() as conn:
        assert (
            conn.scalar(
                text("SELECT count(*) FROM studio.users WHERE auth_user_id=:a"), {"a": auth_id}
            )
            == 1
        )
    assert role_of(service, cookie) == "coach"
    assert audit(db, auth_id) == [("grant_coach", "human", "owner")]


def test_role_revocation_effective(flow):
    from studio.accounts import roles

    service, _, db, auth_id = flow
    cookie = signed_in(service)
    with db.begin() as conn:
        roles.grant_coach(conn, auth_id, actor="owner")
    assert role_of(service, cookie) == "coach"
    with db.begin() as conn:
        roles.revoke_coach(conn, auth_id, actor="owner")
    assert role_of(service, cookie) == "member"
    assert [row[0] for row in audit(db, auth_id)] == ["grant_coach", "revoke_coach"]
