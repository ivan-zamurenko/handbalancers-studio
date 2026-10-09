"""Private auth storage: real crypto, real PostgreSQL and real runtime grants."""

import hashlib
import json
import secrets
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, ProgrammingError

from server.tests.integration.database import test_migration_baseline as baseline
from server.tests.support.actors import role_session
from tools import local_stack

database_engine = baseline.engine
USER = uuid4()
AUTH = uuid4()
ACCESS = "synthetic-access-token-only-for-test"
REFRESH = "synthetic-refresh-token-only-for-test"
VERIFIER = "synthetic-pkce-verifier-only-for-test"


@pytest.fixture(scope="module")
def storage_db(database_engine):
    local_stack.execute_local_sql(
        local_stack.verify_container("test"),
        rf"""
\connect {database_engine.url.database}
GRANT USAGE ON SCHEMA auth TO migration_owner;
GRANT REFERENCES(id) ON auth.users TO migration_owner;
INSERT INTO auth.users VALUES ('{AUTH}');
""",
    )
    with database_engine.begin() as connection:
        command.upgrade(baseline.configuration(connection), "head")
        command.upgrade(baseline.configuration(connection), "head")
        connection.execute(
            text("""
INSERT INTO studio.users(id,auth_user_id,locale,timezone)
VALUES (:id,:auth,'uk','Europe/Kyiv')
"""),
            {"id": USER, "auth": AUTH},
        )
    return database_engine


def api():
    assert (Path(__file__).resolve().parents[3] / "studio/auth/token_store.py").is_file(), (
        "Private token store absent"
    )
    from studio.auth import token_store

    return token_store


@pytest.fixture
def store():
    module = api()
    return module.TokenStore(
        module.TokenCipher("key-1", {"key-1": secrets.token_bytes(32)}),
        allowed_return_paths=frozenset({"/"}),
    )


def create_session(store, session, *, expires_at=None):
    return store.create_session(
        session,
        user_id=USER,
        upstream_session_id=uuid4(),
        access_token=ACCESS,
        refresh_token=REFRESH,
        access_expires_at=datetime.now(UTC) + timedelta(minutes=5),
        expires_at=expires_at or datetime.now(UTC) + timedelta(hours=1),
    )


def create_attempt(store, session, *, expires_at=None):
    return store.create_attempt(
        session,
        provider="google",
        verifier=VERIFIER,
        allowed_return_path="/",
        expires_at=expires_at or datetime.now(UTC) + timedelta(minutes=5),
    )


def test_only_session_hash_stored(storage_db, store, caplog):
    caplog.set_level("INFO", logger="sqlalchemy.engine")
    with role_session(storage_db, "studio_auth_runtime") as session:
        handle = create_session(store, session)
    raw = handle.cookie.get_secret_value()
    assert len(raw) >= 43
    with storage_db.connect() as connection:
        row = (
            connection.execute(
                text("SELECT * FROM studio_private.web_sessions WHERE id=:id"), {"id": handle.id}
            )
            .mappings()
            .one()
        )
        assert row["session_key_hash"] == hashlib.sha256(raw.encode()).hexdigest()
        assert raw not in str(dict(row))
        assert ACCESS not in str(dict(row)) and REFRESH not in str(dict(row))
    assert raw not in repr(handle)
    assert all(secret not in caplog.text for secret in (raw, ACCESS, REFRESH))


def test_encrypted_upstream_tokens(storage_db, store):
    with role_session(storage_db, "studio_auth_runtime") as session:
        handle = create_session(store, session)
        loaded = store.read_session(session, handle.cookie.get_secret_value())
        assert loaded.user_id == USER
        assert loaded.access_token.get_secret_value() == ACCESS
        assert loaded.refresh_token.get_secret_value() == REFRESH
        assert ACCESS not in repr(loaded) and REFRESH not in repr(loaded)
        attempt = create_attempt(store, session)
    with storage_db.connect() as connection:
        row = (
            connection.execute(
                text("SELECT * FROM studio_private.auth_attempts WHERE id=:id"), {"id": attempt.id}
            )
            .mappings()
            .one()
        )
        assert row["user_id"] is None
        assert (
            row["state_hash"]
            == hashlib.sha256(attempt.state.get_secret_value().encode()).hexdigest()
        )
        assert (
            row["nonce_hash"]
            == hashlib.sha256(attempt.binding.get_secret_value().encode()).hexdigest()
        )
        assert VERIFIER not in str(dict(row))
        assert json.loads(row["encrypted_verifier"])["key_id"] == "key-1"
    with role_session(storage_db, "studio_auth_runtime") as session:
        result = store.consume_attempt(
            session,
            attempt.state.get_secret_value(),
            provider="google",
            binding=attempt.binding.get_secret_value(),
        )
        assert result.verifier.get_secret_value() == VERIFIER
        assert VERIFIER not in repr(result)


def test_aead_tamper_context_and_key_rotation():
    module = api()
    old_key, new_key = secrets.token_bytes(32), secrets.token_bytes(32)
    old = module.TokenCipher("old", {"old": old_key})
    context = ("web_sessions", str(uuid4()), str(USER), "encrypted_tokens")
    envelope = old.encrypt(ACCESS, context)
    rotated = module.TokenCipher("new", {"old": old_key, "new": new_key})
    assert rotated.decrypt(envelope, context) == ACCESS
    assert json.loads(rotated.encrypt(ACCESS, context))["key_id"] == "new"
    assert old.encrypt(ACCESS, context) != envelope
    for changed in (
        ("auth_attempts", *context[1:]),
        (context[0], str(uuid4()), *context[2:]),
        (*context[:2], str(uuid4()), context[3]),
        (*context[:3], "encrypted_verifier"),
    ):
        with pytest.raises(module.StoreError):
            rotated.decrypt(envelope, changed)
    tampered = json.loads(envelope)
    tampered["ciphertext"] = tampered["ciphertext"][:-4] + "AAAA"
    for invalid in (
        json.dumps(tampered),
        "not-json",
        json.dumps({**json.loads(envelope), "key_id": "new"}),
    ):
        with pytest.raises(module.StoreError) as error:
            rotated.decrypt(invalid, context)
        assert ACCESS not in str(error.value)
    with pytest.raises(module.StoreError):
        module.TokenCipher("new", {"new": new_key}).decrypt(envelope, context)


@pytest.mark.parametrize("role", ["studio_web", "studio_worker"])
@pytest.mark.parametrize("table", ["web_sessions", "auth_attempts"])
def test_web_role_cannot_read_tokens(storage_db, store, role, table):
    with role_session(storage_db, "studio_auth_runtime") as session:
        create_session(store, session)
        create_attempt(store, session)
    with role_session(storage_db, role, USER) as session:
        with pytest.raises(ProgrammingError) as error:
            session.execute(text(f"SELECT * FROM studio_private.{table}"))
        assert error.value.orig.sqlstate == "42501"
    with storage_db.connect() as connection:
        for public_role in ("anon", "authenticated"):
            assert not connection.scalar(
                text(
                    "SELECT has_table_privilege(:role,:table,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE')"
                ),
                {"role": public_role, "table": f"studio_private.{table}"},
            )


def wait_until_expired(engine, expires_at):
    # Bounded by the one-second TTL supplied by these tests; ciphertext stays valid.
    with engine.connect() as connection:
        connection.execute(text("SET LOCAL statement_timeout='3s'"))
        connection.execute(
            text(
                "SELECT pg_sleep(GREATEST(0, EXTRACT(EPOCH FROM (:expiry - clock_timestamp()))) + 0.02)"
            ),
            {"expiry": expires_at},
        )
        assert connection.scalar(text("SELECT clock_timestamp()")) > expires_at


def test_expired_attempt_rejected(storage_db, store):
    expiry = datetime.now(UTC) + timedelta(seconds=1)
    with role_session(storage_db, "studio_auth_runtime") as session:
        attempt = create_attempt(store, session, expires_at=expiry)
    wait_until_expired(storage_db, expiry)
    with (
        pytest.raises(api().StoreError),
        role_session(storage_db, "studio_auth_runtime") as session,
    ):
        store.consume_attempt(
            session,
            attempt.state.get_secret_value(),
            provider="google",
            binding=attempt.binding.get_secret_value(),
        )


def test_attempt_binding_provider_and_replay(storage_db, store):
    with role_session(storage_db, "studio_auth_runtime") as session:
        attempt = create_attempt(store, session)
    for provider, binding in (
        ("apple", attempt.binding.get_secret_value()),
        ("google", "wrong-binding"),
    ):
        with (
            pytest.raises(api().StoreError),
            role_session(storage_db, "studio_auth_runtime") as session,
        ):
            store.consume_attempt(
                session, attempt.state.get_secret_value(), provider=provider, binding=binding
            )
    with role_session(storage_db, "studio_auth_runtime") as session:
        store.consume_attempt(
            session,
            attempt.state.get_secret_value(),
            provider="google",
            binding=attempt.binding.get_secret_value(),
        )
    with (
        pytest.raises(api().StoreError),
        role_session(storage_db, "studio_auth_runtime") as session,
    ):
        store.consume_attempt(
            session,
            attempt.state.get_secret_value(),
            provider="google",
            binding=attempt.binding.get_secret_value(),
        )


def test_concurrent_consume_returns_one_verifier(storage_db, store):
    with role_session(storage_db, "studio_auth_runtime") as session:
        attempt = create_attempt(store, session)
    barrier = Barrier(2)

    def consume():
        try:
            with role_session(storage_db, "studio_auth_runtime") as session:
                barrier.wait(timeout=5)
                store.consume_attempt(
                    session,
                    attempt.state.get_secret_value(),
                    provider="google",
                    binding=attempt.binding.get_secret_value(),
                )
            return "consumed"
        except api().StoreError:
            return "denied"

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(lambda _: consume(), range(2))) == ["consumed", "denied"]


def test_attempt_rollback_restores_unconsumed_state(storage_db, store):
    with role_session(storage_db, "studio_auth_runtime") as session:
        attempt = create_attempt(store, session)
    with (
        pytest.raises(RuntimeError, match="abort"),
        role_session(storage_db, "studio_auth_runtime") as session,
    ):
        store.consume_attempt(
            session,
            attempt.state.get_secret_value(),
            provider="google",
            binding=attempt.binding.get_secret_value(),
        )
        raise RuntimeError("abort")
    with role_session(storage_db, "studio_auth_runtime") as session:
        assert (
            store.consume_attempt(
                session,
                attempt.state.get_secret_value(),
                provider="google",
                binding=attempt.binding.get_secret_value(),
            ).verifier.get_secret_value()
            == VERIFIER
        )


def test_expired_revoked_and_unknown_session_denied(storage_db, store):
    expiry = datetime.now(UTC) + timedelta(seconds=1)
    with role_session(storage_db, "studio_auth_runtime") as session:
        expired = create_session(store, session, expires_at=expiry)
        revoked = create_session(store, session)
        store.revoke_session(session, revoked.cookie.get_secret_value())
    wait_until_expired(storage_db, expiry)
    for cookie in (expired.cookie.get_secret_value(), revoked.cookie.get_secret_value(), "unknown"):
        with (
            pytest.raises(api().StoreError),
            role_session(storage_db, "studio_auth_runtime") as session,
        ):
            store.read_session(session, cookie)


def test_ciphertext_cannot_move_between_sessions(storage_db, store):
    with role_session(storage_db, "studio_auth_runtime") as session:
        first, second = create_session(store, session), create_session(store, session)
    with storage_db.begin() as connection:
        connection.execute(
            text(
                "UPDATE studio_private.web_sessions SET encrypted_tokens=(SELECT encrypted_tokens FROM studio_private.web_sessions WHERE id=:first) WHERE id=:second"
            ),
            {"first": first.id, "second": second.id},
        )
    with (
        pytest.raises(api().StoreError),
        role_session(storage_db, "studio_auth_runtime") as session,
    ):
        store.read_session(session, second.cookie.get_secret_value())


def test_session_requires_owner_and_unique_hash(storage_db, store):
    with role_session(storage_db, "studio_auth_runtime") as session:
        handle = create_session(store, session)
    with storage_db.begin() as connection:
        for sql, expected_state in (
            ("UPDATE studio_private.web_sessions SET user_id=NULL WHERE id=:id", "23502"),
            (
                "UPDATE studio_private.web_sessions SET user_id='00000000-0000-0000-0000-000000000999' WHERE id=:id",
                "23503",
            ),
            (
                "INSERT INTO studio_private.web_sessions SELECT gen_random_uuid(),session_key_hash,user_id,upstream_session_id,encrypted_tokens,access_expires_at,expires_at,created_at,last_seen_at,revoked_at,row_version FROM studio_private.web_sessions WHERE id=:id",
                "23505",
            ),
        ):
            with pytest.raises(IntegrityError) as error, connection.begin_nested():
                connection.execute(text(sql), {"id": handle.id})
            assert error.value.orig.sqlstate == expected_state


def test_model_matches_head(storage_db, store):
    from studio.db import Base, include_migration_name

    with storage_db.connect() as connection:
        context = MigrationContext.configure(
            connection,
            opts={
                "include_schemas": True,
                "include_name": include_migration_name,
                "version_table_schema": "studio",
                "compare_server_default": True,
            },
        )
        assert compare_metadata(context, Base.metadata) == []


def test_unsafe_return_path_denied(storage_db, store):
    for path in ("https://example.com", "//example.com", "/not-allowed"):
        with (
            pytest.raises(api().StoreError),
            role_session(storage_db, "studio_auth_runtime") as session,
        ):
            store.create_attempt(
                session,
                provider="google",
                verifier=VERIFIER,
                allowed_return_path=path,
                expires_at=datetime.now(UTC) + timedelta(minutes=5),
            )


def test_session_creation_rolls_back(storage_db, store):
    with (
        pytest.raises(RuntimeError, match="abort"),
        role_session(storage_db, "studio_auth_runtime") as session,
    ):
        handle = create_session(store, session)
        raise RuntimeError("abort")
    with storage_db.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT count(*) FROM studio_private.web_sessions WHERE id=:id"),
                {"id": handle.id},
            )
            == 0
        )


def test_key_configuration_is_explicit_and_redacted():
    module = api()
    for active, keys in (("missing", {}), ("one", {"one": b"too-short"})):
        with pytest.raises(module.StoreError) as error:
            module.TokenCipher(active, keys)
        assert "too-short" not in str(error.value)
    cipher = module.TokenCipher("one", {"one": b"x" * 32})
    assert "xxxxxxxx" not in repr(cipher)
