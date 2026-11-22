"""Durable test Checkout intents and narrowly scoped billing writer (S13-02)."""

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
CREATE TABLE studio.checkout_attempts (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 user_id uuid NOT NULL REFERENCES studio.users(id),
 idempotency_key text NOT NULL,
 plan_code text NOT NULL,
 terms_version text NOT NULL,
 state text NOT NULL DEFAULT 'creating',
 created_at timestamptz NOT NULL DEFAULT now(),
 expires_at timestamptz NOT NULL,
 provider_session_id text,
 checkout_url text,
 CONSTRAINT uq_checkout_key UNIQUE(user_id,idempotency_key),
 CONSTRAINT uq_checkout_session UNIQUE(provider_session_id),
 CONSTRAINT ck_checkout_key CHECK(length(idempotency_key) BETWEEN 1 AND 128),
 CONSTRAINT ck_checkout_plan CHECK(plan_code IN ('essential','plus','pro','pro-plus')),
 CONSTRAINT ck_checkout_state CHECK(state IN ('creating','open','pending','completed','expired','failed','needs_reconcile')),
 CONSTRAINT ck_checkout_time CHECK(isfinite(created_at) AND isfinite(expires_at) AND expires_at > created_at),
 CONSTRAINT ck_checkout_terms CHECK(length(terms_version) BETWEEN 1 AND 100)
)
""")
    op.execute(
        "CREATE UNIQUE INDEX uq_checkout_active ON studio.checkout_attempts(user_id) "
        "WHERE state IN ('creating','open','pending','needs_reconcile')"
    )
    op.execute(
        "REVOKE ALL ON studio.checkout_attempts FROM PUBLIC,anon,authenticated,studio_web,studio_auth_runtime,studio_worker"
    )
    op.execute("ALTER TABLE studio.checkout_attempts ENABLE ROW LEVEL SECURITY")
    op.execute("GRANT SELECT ON studio.checkout_attempts TO studio_web")
    op.execute(
        "CREATE POLICY checkout_read_own ON studio.checkout_attempts FOR SELECT TO studio_web "
        "USING (user_id=NULLIF(pg_catalog.current_setting('studio.user_id',true),'')::uuid)"
    )
    op.execute("GRANT SELECT,INSERT,UPDATE ON studio.checkout_attempts TO studio_worker")
    op.execute(
        "CREATE POLICY checkout_billing ON studio.checkout_attempts TO studio_worker USING(true) WITH CHECK(true)"
    )
    op.execute("GRANT SELECT,INSERT ON studio.billing_customers TO studio_worker")
    op.execute(
        "CREATE POLICY customer_billing_read ON studio.billing_customers FOR SELECT TO studio_worker USING(true)"
    )
    op.execute(
        "CREATE POLICY customer_billing_create ON studio.billing_customers FOR INSERT TO studio_worker WITH CHECK(true)"
    )
    op.execute("GRANT SELECT ON studio.subscriptions TO studio_worker")
    op.execute(
        "CREATE POLICY subscription_billing_read ON studio.subscriptions FOR SELECT TO studio_worker USING(true)"
    )


def downgrade() -> None:
    raise RuntimeError("Checkout downgrade would lose payment intents; use a forward repair")
