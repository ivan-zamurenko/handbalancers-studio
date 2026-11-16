"""Own theme preference with optimistic revision (S04-06)."""

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

OWN = "user_id = NULLIF(pg_catalog.current_setting('studio.user_id', true), '')::uuid"


def upgrade() -> None:
    op.execute("""
CREATE TABLE studio.user_preferences (
    user_id uuid PRIMARY KEY REFERENCES studio.users(id),
    theme_preference text NOT NULL DEFAULT 'auto',
    revision integer NOT NULL DEFAULT 1,
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_preferences_theme CHECK (theme_preference IN ('auto', 'light', 'dark')),
    CONSTRAINT ck_preferences_revision CHECK (revision > 0)
)
""")
    op.execute(
        "REVOKE ALL ON studio.user_preferences FROM PUBLIC, anon, authenticated, "
        "studio_web, studio_auth_runtime, studio_worker"
    )
    op.execute("ALTER TABLE studio.user_preferences ENABLE ROW LEVEL SECURITY")
    op.execute("GRANT SELECT, INSERT ON studio.user_preferences TO studio_web")
    op.execute(
        "GRANT UPDATE (theme_preference, revision, updated_at) "
        "ON studio.user_preferences TO studio_web"
    )
    op.execute(
        f"CREATE POLICY preferences_select_own ON studio.user_preferences "
        f"FOR SELECT TO studio_web USING ({OWN})"
    )
    op.execute(
        f"CREATE POLICY preferences_insert_own ON studio.user_preferences "
        f"FOR INSERT TO studio_web WITH CHECK ({OWN})"
    )
    op.execute(
        f"CREATE POLICY preferences_update_own ON studio.user_preferences "
        f"FOR UPDATE TO studio_web USING ({OWN}) WITH CHECK ({OWN})"
    )


def downgrade() -> None:
    raise RuntimeError("Preferences downgrade would drop user settings; use a forward repair")
