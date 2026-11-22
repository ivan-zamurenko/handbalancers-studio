"""One trial per account, reserved before external Checkout (S13-05)."""

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE studio.checkout_attempts ADD COLUMN trial_enabled boolean NOT NULL DEFAULT false, ADD CONSTRAINT uq_checkout_owner UNIQUE(id,user_id)"
    )
    op.execute(
        "ALTER TABLE studio.checkout_attempts ADD COLUMN discovery_attempts integer NOT NULL DEFAULT 0, ADD COLUMN next_discovery timestamptz NOT NULL DEFAULT now(), ADD CONSTRAINT ck_checkout_discovery CHECK(discovery_attempts BETWEEN 0 AND 5)"
    )
    op.execute("""
CREATE TABLE studio.trial_claims (
 user_id uuid PRIMARY KEY REFERENCES studio.users(id),
 attempt_id uuid NOT NULL,
 state text NOT NULL,
 updated_at timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT fk_trial_attempt_owner FOREIGN KEY(attempt_id,user_id) REFERENCES studio.checkout_attempts(id,user_id),
 CONSTRAINT uq_trial_attempt UNIQUE(attempt_id),
 CONSTRAINT ck_trial_state CHECK(state IN ('reserved','claimed','released'))
)
""")
    op.execute(
        "REVOKE ALL ON studio.trial_claims FROM PUBLIC,anon,authenticated,studio_web,studio_auth_runtime,studio_worker"
    )
    op.execute("ALTER TABLE studio.trial_claims ENABLE ROW LEVEL SECURITY")
    op.execute("GRANT SELECT ON studio.trial_claims TO studio_web")
    op.execute(
        "CREATE POLICY trial_read_own ON studio.trial_claims FOR SELECT TO studio_web USING(user_id=NULLIF(pg_catalog.current_setting('studio.user_id',true),'')::uuid)"
    )
    op.execute("GRANT SELECT,INSERT,UPDATE ON studio.trial_claims TO studio_worker")
    op.execute(
        "CREATE POLICY trial_billing ON studio.trial_claims TO studio_worker USING(true) WITH CHECK(true)"
    )
    op.execute("""
CREATE FUNCTION studio_private.keep_claimed_trial() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog AS $$
BEGIN
 IF OLD.state='claimed' AND NEW IS DISTINCT FROM OLD THEN
  RAISE EXCEPTION 'Claimed trial is immutable' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$
""")
    op.execute("REVOKE ALL ON FUNCTION studio_private.keep_claimed_trial() FROM PUBLIC")
    op.execute(
        "CREATE TRIGGER keep_claimed_trial BEFORE UPDATE ON studio.trial_claims FOR EACH ROW EXECUTE FUNCTION studio_private.keep_claimed_trial()"
    )


def downgrade() -> None:
    raise RuntimeError("Trial downgrade would lose one-account history; use a forward repair")
