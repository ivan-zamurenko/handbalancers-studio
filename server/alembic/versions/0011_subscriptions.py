"""Server-only subscription projection (S05-04); no runtime billing writer yet."""

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
CREATE TABLE studio.billing_customers (
    user_id uuid PRIMARY KEY REFERENCES studio.users(id),
    provider_customer_id text NOT NULL,
    CONSTRAINT uq_billing_customer_provider UNIQUE (provider_customer_id),
    CONSTRAINT ck_billing_customer_provider CHECK (length(provider_customer_id) BETWEEN 1 AND 255)
)
""")
    op.execute("""
CREATE TABLE studio.subscriptions (
    user_id uuid PRIMARY KEY REFERENCES studio.billing_customers(user_id),
    provider_subscription_id text NOT NULL,
    plan_code text NOT NULL,
    status text NOT NULL,
    current_period_start timestamptz NOT NULL,
    current_period_end timestamptz NOT NULL,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT uq_subscription_provider UNIQUE (provider_subscription_id),
    CONSTRAINT ck_subscription_provider CHECK (length(provider_subscription_id) BETWEEN 1 AND 255),
    CONSTRAINT ck_subscription_plan CHECK (plan_code IN ('essential', 'plus', 'pro', 'pro-plus')),
    CONSTRAINT ck_subscription_status CHECK (status IN ('active', 'trialing', 'past_due', 'unpaid',
                                                       'canceled', 'paused', 'incomplete',
                                                       'incomplete_expired')),
    CONSTRAINT ck_subscription_trial_plan CHECK (status <> 'trialing' OR
                                                plan_code IN ('essential', 'plus')),
    CONSTRAINT ck_subscription_period CHECK (isfinite(current_period_start) AND
                                            isfinite(current_period_end) AND
                                            current_period_end > current_period_start),
    CONSTRAINT ck_subscription_version CHECK (row_version > 0)
)
""")
    for table in ("billing_customers", "subscriptions"):
        op.execute(
            f"REVOKE ALL ON studio.{table} FROM PUBLIC, anon, authenticated, "
            "studio_web, studio_auth_runtime, studio_worker"
        )
        op.execute(f"ALTER TABLE studio.{table} ENABLE ROW LEVEL SECURITY")
    # Until verified billing ingestion exists, no runtime role may create/update
    # customer or subscription rows. Local tests seed them as the isolated owner.
    op.execute("GRANT SELECT ON studio.subscriptions TO studio_web")
    op.execute("""
CREATE POLICY subscriptions_select_own ON studio.subscriptions
FOR SELECT TO studio_web
USING (user_id = NULLIF(pg_catalog.current_setting('studio.user_id', true), '')::uuid)
""")


def downgrade() -> None:
    raise RuntimeError("Billing downgrade would drop subscription state; use a forward repair")
