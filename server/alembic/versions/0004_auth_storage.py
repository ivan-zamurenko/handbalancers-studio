"""Private encrypted auth records; no keys or raw cookie/state tokens."""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
CREATE TABLE studio_private.web_sessions (
    id uuid PRIMARY KEY,
    session_key_hash text NOT NULL UNIQUE,
    user_id uuid NOT NULL REFERENCES studio.users(id),
    upstream_session_id uuid NOT NULL,
    encrypted_tokens text NOT NULL,
    access_expires_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    revoked_at timestamptz,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT ck_sessions_hash CHECK (session_key_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_sessions_version CHECK (row_version > 0)
)
""")
    op.execute(
        "CREATE INDEX ix_studio_private_web_sessions_user_id ON studio_private.web_sessions(user_id)"
    )
    op.execute("""
CREATE TABLE studio_private.auth_attempts (
    id uuid PRIMARY KEY,
    state_hash text NOT NULL UNIQUE,
    user_id uuid REFERENCES studio.users(id),
    provider text NOT NULL,
    encrypted_verifier text NOT NULL,
    nonce_hash text NOT NULL,
    allowed_return_path text NOT NULL,
    expires_at timestamptz NOT NULL,
    consumed_at timestamptz,
    CONSTRAINT ck_attempts_state CHECK (state_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_attempts_nonce CHECK (nonce_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_attempts_provider CHECK (provider IN ('google', 'apple'))
)
""")
    op.execute(
        "CREATE INDEX ix_studio_private_auth_attempts_user_id ON studio_private.auth_attempts(user_id)"
    )
    for table, mutable in (("web_sessions", "revoked_at"), ("auth_attempts", "consumed_at")):
        op.execute(
            f"REVOKE ALL ON studio_private.{table} FROM PUBLIC, anon, authenticated, studio_web, studio_worker, studio_auth_runtime"
        )
        op.execute(f"ALTER TABLE studio_private.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"GRANT SELECT, INSERT ON studio_private.{table} TO studio_auth_runtime")
        op.execute(f"GRANT UPDATE ({mutable}) ON studio_private.{table} TO studio_auth_runtime")
        op.execute(
            f"CREATE POLICY auth_read ON studio_private.{table} FOR SELECT TO studio_auth_runtime USING (true)"
        )
        op.execute(
            f"CREATE POLICY auth_insert ON studio_private.{table} FOR INSERT TO studio_auth_runtime WITH CHECK (true)"
        )
        op.execute(
            f"CREATE POLICY auth_update ON studio_private.{table} FOR UPDATE TO studio_auth_runtime USING (true) WITH CHECK (true)"
        )


def downgrade() -> None:
    raise RuntimeError(
        "Auth storage downgrade is disabled; use an explicit forward repair migration"
    )
