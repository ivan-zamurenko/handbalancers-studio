"""Executable privileges/RLS tests, against real non-owner PostgreSQL roles."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from server.tests.integration.database import test_migration_baseline as baseline
from server.tests.support.actors import role_session
from tools import local_stack

database_engine = baseline.engine
A, B, COACH, INACTIVE = [UUID(int=i) for i in range(101, 105)]
AUTH = [UUID(int=i) for i in range(1, 11)]
SIGNATURE = "studio_private.provision_member(uuid,text,text,text,text)"
PROVISION = text("""
SELECT studio_private.provision_member(:auth, :first, :last, :locale, :timezone)
""")


@pytest.fixture(scope="module")
def secured(database_engine):
    container = local_stack.verify_container("test")
    identities = ",".join(f"('{value}')" for value in AUTH)
    local_stack.execute_local_sql(
        container,
        rf"""
\connect {database_engine.url.database}
GRANT USAGE ON SCHEMA auth TO migration_owner;
GRANT REFERENCES(id) ON auth.users TO migration_owner;
ALTER TABLE auth.users ADD COLUMN raw_user_meta_data jsonb DEFAULT '{{"role":"coach"}}';
INSERT INTO auth.users(id) VALUES {identities};
""",
    )
    with database_engine.begin() as connection:
        command.upgrade(baseline.configuration(connection), "head")
        command.upgrade(baseline.configuration(connection), "head")
        for user, auth, role, active in zip(
            [A, B, COACH, INACTIVE],
            AUTH,
            ["member", "member", "coach", "member"],
            [True, True, True, False],
            strict=False,
        ):
            connection.execute(
                text("""
INSERT INTO studio.users(id,auth_user_id,role,is_active,locale,timezone)
VALUES (:id,:auth,:role,:active,'uk','Europe/Kyiv')
"""),
                {"id": user, "auth": auth, "role": role, "active": active},
            )
    return database_engine


def provision(session, auth, first=None, last=None):
    assert (
        session.scalar(text("SELECT to_regprocedure(:signature)"), {"signature": SIGNATURE})
        is not None
    ), "Restricted provision function absent"
    return session.scalar(
        PROVISION,
        {
            "auth": auth,
            "first": first,
            "last": last,
            "locale": "uk",
            "timezone": "Europe/Kyiv",
        },
    )


def test_member_cannot_read_other(secured):
    for user in (A, B, COACH):
        with role_session(secured, "studio_web", user) as session:
            assert session.scalars(text("SELECT id FROM studio.users")).all() == [user]
    for user in (None, UUID(int=999), INACTIVE):
        with role_session(secured, "studio_web", user) as session:
            assert session.execute(text("SELECT id FROM studio.users")).all() == []


def test_own_mutable_fields_only(secured):
    with role_session(secured, "studio_web", A) as session:
        assert (
            session.execute(
                text(
                    "UPDATE studio.users SET first_name='Іван',last_name='Тест',locale='en',timezone='Europe/Dublin' WHERE id=:id"
                ),
                {"id": A},
            ).rowcount
            == 1
        )
        assert (
            session.execute(
                text("UPDATE studio.users SET first_name='forbidden' WHERE id=:id"), {"id": B}
            ).rowcount
            == 0
        )
    with role_session(secured, "studio_web", A) as session:
        assert session.execute(
            text("SELECT first_name,last_name,locale,timezone FROM studio.users")
        ).one() == ("Іван", "Тест", "en", "Europe/Dublin")
    with role_session(secured, "studio_web", INACTIVE) as session:
        assert session.execute(text("UPDATE studio.users SET first_name='forbidden'")).rowcount == 0


@pytest.mark.parametrize(
    "assignment",
    [
        "role='coach'",
        "auth_user_id='00000000-0000-0000-0000-000000000009'",
        "is_active=false",
        "id='00000000-0000-0000-0000-000000000999'",
        "created_at=now()",
        "updated_at=now()",
        "row_version=row_version+1",
    ],
)
def test_role_update_denied(secured, assignment):
    with role_session(secured, "studio_web", A) as session:
        with pytest.raises(ProgrammingError) as error, session.begin_nested():
            session.execute(text(f"UPDATE studio.users SET {assignment} WHERE id=:id"), {"id": A})
        assert error.value.orig.sqlstate == "42501"


def test_insert_delete_truncate_denied(secured):
    for statement in (
        "INSERT INTO studio.users(auth_user_id,locale,timezone) VALUES ('00000000-0000-0000-0000-000000000009','uk','UTC')",
        "DELETE FROM studio.users",
        "TRUNCATE studio.users",
    ):
        with role_session(secured, "studio_web", A) as session:
            with pytest.raises(ProgrammingError) as error:
                session.execute(text(statement))
            assert error.value.orig.sqlstate == "42501"


def test_metadata_coach_ignored(secured):
    with role_session(secured, "studio_auth_runtime") as session:
        user_id = provision(session, AUTH[4], "OAuth", None)
    with role_session(secured, "studio_web", user_id) as session:
        assert session.execute(
            text("SELECT role,first_name,last_name FROM studio.users")
        ).one() == ("member", "OAuth", None)


def test_provision_retry_preserves_existing_profile(secured):
    with role_session(secured, "studio_auth_runtime") as session:
        assert provision(session, AUTH[2], "Overwrite", "Denied") == COACH
    with role_session(secured, "studio_web", COACH) as session:
        assert session.execute(text("SELECT role,first_name FROM studio.users")).one() == (
            "coach",
            None,
        )


def test_provision_concurrent_and_rollback(secured):
    barrier = Barrier(2)

    def create():
        with role_session(secured, "studio_auth_runtime") as session:
            session.execute(text("SET LOCAL statement_timeout='5s'"))
            barrier.wait(timeout=5)
            return provision(session, AUTH[5])

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: create(), range(2)))
    assert results[0] == results[1]
    with (
        pytest.raises(RuntimeError, match="abort"),
        role_session(secured, "studio_auth_runtime") as session,
    ):
        provision(session, AUTH[6])
        raise RuntimeError("abort")
    with secured.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT count(*) FROM studio.users WHERE auth_user_id=:id"), {"id": AUTH[5]}
            )
            == 1
        )
        assert (
            connection.scalar(
                text("SELECT count(*) FROM studio.users WHERE auth_user_id=:id"), {"id": AUTH[6]}
            )
            == 0
        )


def test_auth_worker_no_direct_table_access(secured):
    for role in ("studio_auth_runtime", "studio_worker"):
        with role_session(secured, role, A) as session:
            with pytest.raises(ProgrammingError) as error:
                session.execute(text("SELECT * FROM studio.users"))
            assert error.value.orig.sqlstate == "42501"


def test_provision_privileges_and_owner(secured):
    with secured.connect() as connection:
        row = connection.execute(
            text("""
SELECT pg_get_userbyid(proowner),prosecdef,proconfig
FROM pg_proc WHERE oid=to_regprocedure(:signature)
"""),
            {"signature": SIGNATURE},
        ).one_or_none()
        assert row is not None, "Restricted provision function absent"
        assert row[0] == "migration_owner" and row[1] is True
        assert "search_path=pg_catalog, pg_temp" in row[2]
        for role, allowed in (
            ("studio_auth_runtime", True),
            ("studio_worker", False),
            ("studio_web", False),
            ("anon", False),
            ("authenticated", False),
        ):
            assert (
                connection.scalar(
                    text("SELECT has_function_privilege(:role,:signature,'EXECUTE')"),
                    {"role": role, "signature": SIGNATURE},
                )
                is allowed
            )
    for role in ("studio_web", "studio_worker"):
        with role_session(secured, role, A) as session:
            with pytest.raises(ProgrammingError) as error:
                provision(session, AUTH[7])
            assert error.value.orig.sqlstate == "42501"


def test_public_api_database_denied(secured):
    with secured.connect() as connection:
        for role in ("anon", "authenticated"):
            for schema in ("studio", "studio_private"):
                assert not connection.scalar(
                    text("SELECT has_schema_privilege(:role,:schema,'USAGE')"),
                    {"role": role, "schema": schema},
                )
            assert not connection.scalar(
                text(
                    "SELECT has_table_privilege(:role,'studio.users','SELECT,INSERT,UPDATE,DELETE,TRUNCATE')"
                ),
                {"role": role},
            )
    # Execute as real public roles without granting them to the operator login.
    local_stack.execute_local_sql(
        local_stack.verify_container("test"),
        rf"""
\connect {secured.url.database}
BEGIN;
SET LOCAL ROLE anon;
DO $probe$ BEGIN
  BEGIN PERFORM id FROM studio.users; RAISE EXCEPTION 'anon read succeeded';
  EXCEPTION WHEN insufficient_privilege THEN NULL; END;
END $probe$;
RESET ROLE;
SET LOCAL ROLE authenticated;
DO $probe$ BEGIN
  BEGIN PERFORM id FROM studio.users; RAISE EXCEPTION 'authenticated read succeeded';
  EXCEPTION WHEN insufficient_privilege THEN NULL; END;
END $probe$;
ROLLBACK;
""",
    )


def test_failed_edit_rolls_back(secured):
    with role_session(secured, "studio_web", B) as session:
        before = session.scalar(text("SELECT first_name FROM studio.users"))
    with (
        pytest.raises(RuntimeError, match="abort"),
        role_session(secured, "studio_web", B) as session,
    ):
        session.execute(text("UPDATE studio.users SET first_name='rollback'"))
        raise RuntimeError("abort")
    with role_session(secured, "studio_web", B) as session:
        assert session.scalar(text("SELECT first_name FROM studio.users")) == before


def test_provision_fixed_path_and_no_table_grants(secured):
    with role_session(secured, "studio_auth_runtime") as session:
        session.execute(text("CREATE TEMP TABLE users (id uuid, role text) ON COMMIT DROP"))
        session.execute(text("SET LOCAL search_path = pg_temp, public"))
        user_id = provision(session, AUTH[7])
        assert session.scalar(text("SELECT count(*) FROM pg_temp.users")) == 0
        with pytest.raises(ProgrammingError) as error, session.begin_nested():
            session.execute(text("UPDATE studio.users SET role='coach'"))
        assert error.value.orig.sqlstate == "42501"
    with role_session(secured, "studio_web", user_id) as session:
        assert session.scalar(text("SELECT role FROM studio.users")) == "member"


def test_concurrent_member_edits_remain_isolated(secured):
    barrier = Barrier(2)

    def edit(user):
        with role_session(secured, "studio_web", user) as session:
            session.execute(text("SET LOCAL statement_timeout='5s'"))
            barrier.wait(timeout=5)
            rows = (
                session.execute(
                    text("UPDATE studio.users SET last_name=:value RETURNING id"),
                    {"value": str(user)},
                )
                .scalars()
                .all()
            )
            return rows

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert list(executor.map(edit, [A, B])) == [[A], [B]]


def test_inactive_profile_retry_does_not_reactivate(secured):
    with role_session(secured, "studio_auth_runtime") as session:
        assert provision(session, AUTH[3], "Changed", "Changed") == INACTIVE
    with secured.connect() as connection:
        assert connection.execute(
            text("SELECT is_active,first_name,last_name FROM studio.users WHERE id=:id"),
            {"id": INACTIVE},
        ).one() == (False, None, None)
    with role_session(secured, "studio_web", INACTIVE) as session:
        assert session.execute(text("SELECT * FROM studio.users")).all() == []
