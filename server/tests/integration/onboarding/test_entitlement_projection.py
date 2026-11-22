"""S05-04: trusted projection, temporal expiry, readiness and database isolation."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from importlib.util import find_spec
from threading import Barrier
from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, ProgrammingError
from studio.shared.context import Actor

from server.tests.integration.database.test_auth_storage import (  # noqa: F401
    USER,
    database_engine,
    storage_db,
)
from server.tests.integration.database.test_migration_baseline import configuration
from server.tests.support.actors import role_session

NOW = datetime(2026, 11, 22, tzinfo=UTC)
PLANS = ("essential", "plus", "pro", "pro-plus")
CAPABILITIES = frozenset(
    {
        "published_catalog",
        "training_write",
        "program_builder",
        "ai_guidance",
        "weekly_human_review",
        "personal_chat",
        "coaching_calls",
    }
)


@pytest.fixture
def api():
    assert find_spec("studio.billing") is not None, "Server entitlement policy is absent"
    from studio.billing import entitlements

    return entitlements


def projection(api, plan="plus", status="active", **changes):
    return api.SubscriptionProjection(
        **{
            "user_id": USER,
            "plan_code": plan,
            "status": status,
            "current_period_start": NOW - timedelta(days=1),
            "current_period_end": NOW + timedelta(days=6),
            "row_version": 1,
            **changes,
        }
    )


def rights(api, subscription, ready=CAPABILITIES, now=NOW, actor=None):
    return api.evaluate_entitlements(
        actor=actor or Actor(USER),
        subscription=subscription,
        ready=ready,
        now=now,
    )


@pytest.mark.parametrize(
    "plan,status",
    [*((p, "active") for p in PLANS), ("essential", "trialing"), ("plus", "trialing")],
)
def test_catalog_all_paid_tiers(api, plan, status):
    result = rights(api, projection(api, plan, status))
    assert "published_catalog" in result.capabilities
    assert "training_write" in result.capabilities
    assert result.can_read_own_profile and result.can_read_own_history


@pytest.mark.parametrize(
    "status",
    ["past_due", "unpaid", "canceled", "paused", "incomplete", "incomplete_expired", "unknown"],
)
def test_inactive_read_only(api, status):
    result = rights(api, projection(api, status=status))
    assert result.can_read_own_profile and result.can_read_own_history
    assert result.capabilities == frozenset()


def test_missing_subscription_keeps_own_reads(api):
    result = rights(api, None)
    assert result.can_read_own_profile and result.can_read_own_history
    assert not result.capabilities


@pytest.mark.parametrize("plan", ["essential", "plus"])
def test_plus_no_human_review(api, plan):
    result = rights(api, projection(api, plan))
    assert "weekly_human_review" not in result.capabilities
    assert ("ai_guidance" in result.capabilities) == (plan == "plus")


def test_coach_and_pro_plus_capabilities(api):
    pro = rights(api, projection(api, "pro")).capabilities
    premium = rights(api, projection(api, "pro-plus")).capabilities
    assert "weekly_human_review" in pro
    assert {"personal_chat", "coaching_calls"}.isdisjoint(pro)
    assert {"weekly_human_review", "personal_chat", "coaching_calls"} <= premium


@pytest.mark.parametrize("plan", PLANS)
def test_unready_feature_closed(api, plan):
    assert not rights(api, projection(api, plan), ready=frozenset()).capabilities
    for capability in CAPABILITIES:
        result = rights(api, projection(api, plan), ready=CAPABILITIES - {capability})
        assert capability not in result.capabilities
    # Unknown flags cannot create rights; default readiness is closed.
    assert not rights(api, projection(api, plan), ready=frozenset({"invented"})).capabilities
    assert not api.evaluate_entitlements(
        actor=Actor(USER),
        subscription=projection(api, plan),
        now=NOW,
    ).capabilities


@pytest.mark.parametrize(
    "change",
    [
        {"current_period_end": NOW},
        {"current_period_end": NOW - timedelta(seconds=1)},
        {"current_period_start": NOW + timedelta(seconds=1)},
        {"plan_code": "invented"},
        {"user_id": uuid4()},
        {"plan_code": "pro", "status": "trialing"},
        {"plan_code": "pro-plus", "status": "trialing"},
    ],
)
def test_expired_future_foreign_or_invalid_projection_closed(api, change):
    assert not rights(api, projection(api, **change)).capabilities


def test_period_start_inclusive_and_expiry_rechecked(api):
    sub = projection(api, current_period_start=NOW)
    assert rights(api, sub).capabilities
    assert not rights(api, sub, now=sub.current_period_end).capabilities
    assert not rights(api, replace(sub, status="canceled", row_version=2)).capabilities


@pytest.fixture
def seeded(api, storage_db):  # noqa: F811
    # All synthetic subscription writes use the isolated test operator, never runtime.
    with storage_db.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO studio.billing_customers (user_id, provider_customer_id) "
                "VALUES (:u, 'synthetic-customer')"
            ),
            {"u": USER},
        )
        conn.execute(
            text(
                "INSERT INTO studio.subscriptions "
                "(user_id, provider_subscription_id, plan_code, status, "
                "current_period_start, current_period_end) "
                "VALUES (:u, 'synthetic-subscription', 'plus', 'active', :s, :e)"
            ),
            {"u": USER, "s": NOW - timedelta(days=1), "e": NOW + timedelta(days=6)},
        )
    try:
        yield storage_db
    finally:
        with storage_db.begin() as conn:
            conn.execute(text("DELETE FROM studio.subscriptions WHERE user_id=:u"), {"u": USER})
            conn.execute(text("DELETE FROM studio.billing_customers WHERE user_id=:u"), {"u": USER})


def test_client_tier_ignored(api, seeded):
    from studio.billing.models import Subscription

    with role_session(seeded, "studio_web", USER) as session:
        loaded = api.load_subscription(session, Actor(USER))
        assert loaded.plan_code == "plus" and loaded.row_version == 1
        assert "weekly_human_review" not in rights(api, loaded).capabilities
        # A request dict is not a projection, even if it claims the correct owner.
        for fake in (
            {"plan_code": "pro-plus", "role": "coach", "user_id": USER},
            {"plan_code": "pro-plus", "status": "active"},
        ):
            with pytest.raises(TypeError):
                rights(api, fake)
        # Even a query without an owner predicate cannot see a foreign subscription.
        assert len(session.scalars(select(Subscription)).all()) == 1
    with role_session(seeded, "studio_web", uuid4()) as session:
        assert session.scalars(select(Subscription)).all() == []
        assert api.load_subscription(session, Actor(USER)) is None
    with role_session(seeded, "studio_web") as session:
        assert session.scalars(select(Subscription)).all() == []


@pytest.mark.parametrize(
    "role", ["studio_web", "studio_auth_runtime", "anon", "authenticated"]
)
@pytest.mark.parametrize("verb", ["INSERT", "UPDATE", "DELETE"])
def test_runtime_cannot_grant_or_change_subscription(api, seeded, role, verb):
    queries = {
        "INSERT": "INSERT INTO studio.subscriptions SELECT * FROM studio.subscriptions",
        "UPDATE": "UPDATE studio.subscriptions SET plan_code='pro-plus'",
        "DELETE": "DELETE FROM studio.subscriptions",
    }
    # Real PostgreSQL privileges; no mocked SDK or application authorization.
    with seeded.begin() as conn:
        with pytest.raises(ProgrammingError) as error, conn.begin_nested():
            conn.exec_driver_sql(f"SET LOCAL ROLE {role}")
            conn.execute(text("SELECT set_config('studio.user_id', :u, true)"), {"u": str(USER)})
            conn.execute(text(queries[verb]))
        assert error.value.orig.sqlstate == "42501"
        assert conn.scalar(text("SELECT plan_code FROM studio.subscriptions")) == "plus"
        for table in ("billing_customers", "subscriptions"):
            assert conn.scalar(
                text("SELECT relrowsecurity FROM pg_class WHERE oid=to_regclass(:t)"),
                {"t": f"studio.{table}"},
            )
            expected = role == "studio_worker" and table == "billing_customers" and verb == "INSERT"
            assert (
                bool(
                    conn.scalar(
                        text("SELECT has_table_privilege(:r, :t, :v)"),
                        {"r": role, "t": f"studio.{table}", "v": verb},
                    )
                )
                == expected
            )
        # S13-02 adds the verified billing worker; public/auth/web still cannot read customers.
        assert bool(
            conn.scalar(
                text("SELECT has_table_privilege(:r, 'studio.billing_customers', 'SELECT')"),
                {"r": role},
            )
        ) == (role == "studio_worker")


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE studio.subscriptions SET plan_code='fake'",
        "UPDATE studio.subscriptions SET status='fake'",
        "UPDATE studio.subscriptions SET row_version=0",
        "UPDATE studio.subscriptions SET current_period_end=current_period_start",
        "UPDATE studio.subscriptions SET current_period_end='infinity'",
        "UPDATE studio.subscriptions SET plan_code='pro', status='trialing'",
        "INSERT INTO studio.subscriptions SELECT * FROM studio.subscriptions",
    ],
)
def test_database_rejects_invalid_projection_and_rolls_back(api, seeded, sql):
    with seeded.begin() as conn:
        with pytest.raises(IntegrityError), conn.begin_nested():
            conn.execute(text(sql))
        assert conn.scalar(text("SELECT plan_code FROM studio.subscriptions")) == "plus"
        assert conn.scalar(text("SELECT count(*) FROM studio.subscriptions")) == 1


def test_fresh_database_projection_observes_revocation(api, seeded):
    with role_session(seeded, "studio_web", USER) as session:
        assert rights(api, api.load_subscription(session, Actor(USER))).capabilities
        with seeded.begin() as writer:
            writer.execute(text("UPDATE studio.subscriptions SET status='canceled', row_version=2"))
        updated = api.load_subscription(session, Actor(USER))
        assert updated.row_version == 2
        assert not rights(api, updated).capabilities


def test_concurrent_duplicate_subscription_has_one_winner(api, seeded):
    with seeded.begin() as conn:
        conn.execute(text("DELETE FROM studio.subscriptions"))
    barrier = Barrier(2)

    def insert(index):
        try:
            with seeded.begin() as conn:
                conn.execute(text("SET LOCAL statement_timeout='5s'"))
                barrier.wait(timeout=5)
                conn.execute(
                    text(
                        "INSERT INTO studio.subscriptions "
                        "(user_id, provider_subscription_id, plan_code, status, "
                        "current_period_start, current_period_end) "
                        "VALUES (:u, :p, 'plus', 'active', :s, :e)"
                    ),
                    {
                        "u": USER,
                        "p": f"synthetic-race-{index}",
                        "s": NOW,
                        "e": NOW + timedelta(days=30),
                    },
                )
            return "committed"
        except IntegrityError as error:
            assert error.orig.sqlstate == "23505"
            return "duplicate"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(insert, (1, 2))) == ["committed", "duplicate"]
    with seeded.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM studio.subscriptions")) == 1


def test_subscription_requires_existing_customer(api, seeded):
    with seeded.begin() as conn:
        with pytest.raises(IntegrityError) as error, conn.begin_nested():
            conn.execute(text("UPDATE studio.subscriptions SET user_id=:u"), {"u": uuid4()})
        assert error.value.orig.sqlstate == "23503"


def test_downgrade_preserves_subscription(api, seeded):
    with seeded.begin() as conn:
        with pytest.raises(RuntimeError, match="forward repair"), conn.begin_nested():
            command.downgrade(configuration(conn), "0010")
        assert conn.scalar(text("SELECT count(*) FROM studio.subscriptions")) == 1
        assert conn.scalar(text("SELECT version_num FROM studio.alembic_version")) == "0014"
