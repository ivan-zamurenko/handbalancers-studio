"""Encrypted durable Stripe inbox, worker-only (S13-03)."""

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
CREATE TABLE studio_private.webhook_events (
 event_id text PRIMARY KEY,
 event_type text NOT NULL,
 object_id text NOT NULL,
 encrypted_payload text NOT NULL,
 state text NOT NULL DEFAULT 'pending',
 attempts integer NOT NULL DEFAULT 0,
 received_at timestamptz NOT NULL DEFAULT now(),
 next_retry timestamptz NOT NULL DEFAULT now(),
 lease_token uuid,
 lease_until timestamptz,
 last_error text,
 CONSTRAINT ck_webhook_event_id CHECK(length(event_id) BETWEEN 4 AND 255),
 CONSTRAINT ck_webhook_object_id CHECK(length(object_id) BETWEEN 1 AND 255),
 CONSTRAINT ck_webhook_type CHECK(length(event_type) BETWEEN 1 AND 100),
 CONSTRAINT ck_webhook_state CHECK(state IN ('pending','processing','processed','failed','ignored')),
 CONSTRAINT ck_webhook_attempts CHECK(attempts BETWEEN 0 AND 10)
)
""")
    op.execute("CREATE INDEX ix_webhook_retry ON studio_private.webhook_events(state,next_retry)")
    op.execute(
        "REVOKE ALL ON studio_private.webhook_events FROM PUBLIC,anon,authenticated,studio_web,studio_auth_runtime,studio_worker"
    )
    op.execute("ALTER TABLE studio_private.webhook_events ENABLE ROW LEVEL SECURITY")
    op.execute("GRANT SELECT,INSERT,UPDATE ON studio_private.webhook_events TO studio_worker")
    op.execute(
        "CREATE POLICY webhook_billing ON studio_private.webhook_events TO studio_worker USING(true) WITH CHECK(true)"
    )


def downgrade() -> None:
    raise RuntimeError("Webhook downgrade would lose pending events; use a forward repair")
