"""Append-only payment/refund facts, separate from current entitlement (S13-10)."""

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
CREATE TABLE studio.payments (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 user_id uuid NOT NULL REFERENCES studio.billing_customers(user_id),
 provider_payment_id text NOT NULL,
 provider_invoice_id text NOT NULL,
 provider_payment_intent_id text NOT NULL,
 provider_customer_id text NOT NULL,
 provider_subscription_id text NOT NULL,
 provider_charge_id text NOT NULL,
 plan_code text NOT NULL,
 amount_minor bigint NOT NULL,
 currency text NOT NULL,
 paid_at timestamptz NOT NULL,
 recorded_at timestamptz NOT NULL DEFAULT now(),
 livemode boolean NOT NULL,
 CONSTRAINT uq_payment_provider UNIQUE(provider_payment_id),
 CONSTRAINT uq_payment_intent UNIQUE(provider_payment_intent_id),
 CONSTRAINT uq_payment_owner UNIQUE(id,user_id),
 CONSTRAINT ck_payment_plan CHECK(plan_code IN ('essential','plus','pro','pro-plus')),
 CONSTRAINT ck_payment_amount CHECK(amount_minor > 0),
 CONSTRAINT ck_payment_currency CHECK(currency ~ '^[a-z]{3}$'),
 CONSTRAINT ck_payment_time CHECK(isfinite(paid_at) AND isfinite(recorded_at))
)
""")
    op.execute("CREATE INDEX ix_payment_owner_time ON studio.payments(user_id,paid_at,id)")
    op.execute("""
CREATE TABLE studio.payment_refunds (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 payment_id uuid NOT NULL,
 user_id uuid NOT NULL,
 provider_refund_id text NOT NULL,
 status text NOT NULL,
 amount_minor bigint NOT NULL,
 currency text NOT NULL,
 created_at timestamptz NOT NULL,
 recorded_at timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT fk_refund_payment_owner FOREIGN KEY(payment_id,user_id) REFERENCES studio.payments(id,user_id),
 CONSTRAINT uq_refund_provider UNIQUE(provider_refund_id),
 CONSTRAINT ck_refund_status CHECK(status IN ('pending','requires_action','succeeded','failed','canceled')),
 CONSTRAINT ck_refund_amount CHECK(amount_minor > 0),
 CONSTRAINT ck_refund_currency CHECK(currency ~ '^[a-z]{3}$'),
 CONSTRAINT ck_refund_time CHECK(isfinite(created_at) AND isfinite(recorded_at))
)
""")
    op.execute("CREATE INDEX ix_refund_payment ON studio.payment_refunds(payment_id,user_id)")
    op.execute("CREATE INDEX ix_refund_owner ON studio.payment_refunds(user_id)")
    op.execute("""
CREATE FUNCTION studio_private.immutable_payment_fact() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog AS $$
BEGIN
 IF TG_TABLE_NAME='payment_refunds' AND
    (to_jsonb(NEW)-'status') IS NOT DISTINCT FROM (to_jsonb(OLD)-'status') THEN
  RETURN NEW;
 END IF;
 RAISE EXCEPTION 'Financial facts are immutable' USING ERRCODE='23514';
END $$
""")
    op.execute("REVOKE ALL ON FUNCTION studio_private.immutable_payment_fact() FROM PUBLIC")
    for table in ("payments", "payment_refunds"):
        op.execute(
            f"REVOKE ALL ON studio.{table} FROM PUBLIC,anon,authenticated,studio_web,studio_auth_runtime,studio_worker"
        )
        op.execute(f"ALTER TABLE studio.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"GRANT SELECT ON studio.{table} TO studio_web")
        op.execute(
            f"CREATE POLICY {table}_own ON studio.{table} FOR SELECT TO studio_web USING(user_id=NULLIF(pg_catalog.current_setting('studio.user_id',true),'')::uuid)"
        )
        op.execute(f"GRANT SELECT,INSERT ON studio.{table} TO studio_worker")
        op.execute(
            f"CREATE POLICY {table}_worker_read ON studio.{table} FOR SELECT TO studio_worker USING(true)"
        )
        op.execute(
            f"CREATE POLICY {table}_worker_insert ON studio.{table} FOR INSERT TO studio_worker WITH CHECK(true)"
        )
        op.execute(
            f"CREATE TRIGGER immutable_payment_fact BEFORE UPDATE ON studio.{table} FOR EACH ROW EXECUTE FUNCTION studio_private.immutable_payment_fact()"
        )

    op.execute("GRANT UPDATE(status) ON studio.payment_refunds TO studio_worker")
    op.execute(
        "CREATE POLICY refund_status_worker ON studio.payment_refunds FOR UPDATE TO studio_worker USING(true) WITH CHECK(true)"
    )


def downgrade() -> None:
    raise RuntimeError("Financial history must be retained; use a forward repair")
