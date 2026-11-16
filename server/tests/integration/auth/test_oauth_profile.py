"""Profile fields come from a verified exchange; PostgreSQL remains the source of truth."""

import asyncio

import pytest
from sqlalchemy import text

from server.tests.integration.auth.test_oauth_flow import flow  # noqa: F401
from server.tests.integration.database.test_auth_storage import storage_db, database_engine  # noqa: F401


def with_metadata(service, metadata):
    exchange = service.gateway.oauth_exchange

    async def enriched(*args):
        payload = await exchange(*args)
        payload["user"]["user_metadata"] = metadata
        return payload

    service.gateway.oauth_exchange = enriched


def login(service, provider="google"):
    attempt = service.start(provider, "/plans")
    return asyncio.run(
        service.finish(
            provider, attempt.attempt, attempt.binding.get_secret_value(), "synthetic-code"
        )
    )


def test_google_display_name_preserved_without_guessing_surname(flow):
    service, _, db, _ = flow
    with_metadata(
        service, {"full_name": "  Марія   де ла Крус  ", "role": "coach", "is_active": False}
    )
    result = login(service)
    profile = asyncio.run(service.session_profile(result.cookie.get_secret_value()))
    assert profile.get("display_name") == "Марія де ла Крус"
    assert profile["first_name"] is None and profile["last_name"] is None
    assert profile["role"] == "member"
    assert not profile["profile_complete"]
    with db.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT display_name FROM studio.users WHERE id=:id"), {"id": result.user_id}
            )
            == "Марія де ла Крус"
        )


def test_explicit_names_imported_and_manual_edits_preserved(flow):
    service, _, db, _ = flow
    metadata = {"given_name": " Олена ", "family_name": " Коваль ", "name": "Олена Коваль"}
    with_metadata(service, metadata)
    first = login(service)
    assert first.profile_complete
    with db.begin() as c:
        row = c.execute(
            text("SELECT first_name,last_name FROM studio.users WHERE id=:id"),
            {"id": first.user_id},
        ).one()
        assert row == ("Олена", "Коваль")
        c.execute(
            text(
                "UPDATE studio.users SET first_name='Моє ім’я',display_name='Мій профіль' WHERE id=:id"
            ),
            {"id": first.user_id},
        )
    metadata.update(given_name="Provider change", name="Provider overwrite", role="coach")
    second = login(service)
    assert second.user_id == first.user_id
    profile = asyncio.run(service.session_profile(second.cookie.get_secret_value()))
    assert (
        profile["first_name"],
        profile["last_name"],
        profile["display_name"],
        profile["role"],
    ) == ("Моє ім’я", "Коваль", "Мій профіль", "member")


def test_missing_names_can_fill_later_without_duplicate(flow):
    service, _, db, auth_id = flow
    metadata = {}
    with_metadata(service, metadata)
    first = login(service, "google")
    assert not first.profile_complete
    metadata.update(first_name="Іван", last_name="Петренко", full_name="Іван Петренко")
    second = login(service, "google")
    profile = asyncio.run(service.session_profile(second.cookie.get_secret_value()))
    assert profile.get("display_name") == "Іван Петренко"
    assert second.profile_complete
    with db.connect() as c:
        assert (
            c.scalar(
                text("SELECT count(*) FROM studio.users WHERE auth_user_id=:id"), {"id": auth_id}
            )
            == 1
        )


@pytest.mark.parametrize(
    "metadata",
    [
        None,
        ["bad"],
        {"given_name": {"role": "coach"}, "full_name": False},
        {"given_name": "a" * 101, "family_name": "bad\x00name", "full_name": "x" * 201},
    ],
)
def test_malformed_optional_names_do_not_break_login(flow, metadata):
    service, _, _, _ = flow
    with_metadata(service, metadata)
    result = login(service)
    profile = asyncio.run(service.session_profile(result.cookie.get_secret_value()))
    assert profile["first_name"] is None and profile["last_name"] is None
    assert profile.get("display_name") is None
    assert profile["role"] == "member"


def test_repeat_login_does_not_churn_revision(flow):
    service, _, db, _ = flow
    with_metadata(service, {"name": "Марія Коваль"})
    first = login(service)
    with db.connect() as c:
        before = c.execute(
            text("SELECT row_version,updated_at FROM studio.users WHERE id=:id"),
            {"id": first.user_id},
        ).one()
    second = login(service)
    with db.connect() as c:
        assert (
            c.execute(
                text("SELECT row_version,updated_at FROM studio.users WHERE id=:id"),
                {"id": second.user_id},
            ).one()
            == before
        )


def test_concurrent_fill_is_atomic_and_roles_cannot_import(flow):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from sqlalchemy.exc import ProgrammingError
    from server.tests.support.actors import role_session

    service, _, db, auth_id = flow
    first = login(service)
    barrier = Barrier(2)

    def fill(name):
        with role_session(db, "studio_auth_runtime") as session:
            session.execute(text("SET LOCAL statement_timeout='5s'"))
            barrier.wait(timeout=5)
            return session.scalar(
                text("SELECT studio_private.provision_oauth_member(:id,:name,:name,:name)"),
                {"id": auth_id, "name": name},
            )

    with ThreadPoolExecutor(2) as pool:
        ids = list(pool.map(fill, ["First", "Second"]))
    assert ids == [first.user_id, first.user_id]
    with db.connect() as c:
        row = c.execute(
            text(
                "SELECT first_name,last_name,display_name,row_version FROM studio.users WHERE id=:id"
            ),
            {"id": first.user_id},
        ).one()
        assert row in [("First", "First", "First", 2), ("Second", "Second", "Second", 2)]
        for role in ["anon", "authenticated", "studio_web", "studio_worker"]:
            for signature in [
                "studio_private.provision_oauth_member(uuid,text,text,text)",
                "studio_private.auth_profile(uuid)",
            ]:
                assert not c.scalar(
                    text("SELECT has_function_privilege(:role,:fn,'EXECUTE')"),
                    {"role": role, "fn": signature},
                )
    for role in ["studio_web", "studio_worker"]:
        with role_session(db, role) as s, pytest.raises(ProgrammingError):
            s.execute(
                text("SELECT studio_private.provision_oauth_member(:id,'Bad','Bad','Bad')"),
                {"id": auth_id},
            )


def test_unverified_metadata_cannot_create_profile(flow):
    from studio.auth.jwt import InvalidIdentity

    service, _, db, auth_id = flow
    exchange = service.gateway.oauth_exchange

    async def mismatched(*args):
        from uuid import uuid4

        data = await exchange(*args)
        data["user"]["id"] = str(uuid4())
        data["user"]["user_metadata"] = {"name": "Untrusted", "role": "coach"}
        return data

    service.gateway.oauth_exchange = mismatched
    with pytest.raises(InvalidIdentity):
        login(service)
    with db.connect() as c:
        assert (
            c.scalar(
                text("SELECT count(*) FROM studio.users WHERE auth_user_id=:id"), {"id": auth_id}
            )
            == 0
        )
