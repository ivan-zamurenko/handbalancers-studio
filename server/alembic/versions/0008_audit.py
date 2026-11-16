"""Operator-only audit trail; first use: coach role bootstrap (S04-05)."""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # analysis_run_id FK is added only in the AI stage (card S04-05).
    op.execute("""
CREATE TABLE studio_private.audit_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    occurred_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    actor_type text NOT NULL,
    actor text NOT NULL,
    action text NOT NULL,
    subject_user_id uuid NOT NULL REFERENCES studio.users(id),
    CONSTRAINT ck_audit_actor_type CHECK (actor_type IN ('human', 'system')),
    CONSTRAINT ck_audit_actor CHECK (length(actor) BETWEEN 1 AND 100),
    CONSTRAINT ck_audit_action CHECK (action ~ '^[a-z_]{1,64}$')
)
""")
    op.execute(
        "CREATE INDEX ix_studio_private_audit_events_subject_user_id "
        "ON studio_private.audit_events(subject_user_id)"
    )
    op.execute(
        "REVOKE ALL ON studio_private.audit_events FROM PUBLIC, anon, authenticated, "
        "studio_web, studio_worker, studio_auth_runtime"
    )
    op.execute("ALTER TABLE studio_private.audit_events ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    raise RuntimeError("Audit downgrade would drop history; use an explicit forward repair")
