"""Narrow current-profile read for verified server sessions, without table grants."""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
CREATE FUNCTION studio_private.auth_profile(p_user_id uuid)
RETURNS TABLE (id uuid, auth_user_id uuid, first_name text, last_name text,
    role text, locale text, timezone text)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $function$
    SELECT u.id,u.auth_user_id,u.first_name,u.last_name,u.role,u.locale,u.timezone
    FROM studio.users u WHERE u.id=p_user_id AND u.is_active
$function$;
REVOKE ALL ON FUNCTION studio_private.auth_profile(uuid)
FROM PUBLIC, anon, authenticated, studio_web, studio_worker;
GRANT EXECUTE ON FUNCTION studio_private.auth_profile(uuid) TO studio_auth_runtime;
""")

    op.execute("""
CREATE TABLE studio_private.auth_rate_limits (
    bucket_hash text PRIMARY KEY, window_start timestamptz NOT NULL,
    attempts integer NOT NULL CHECK (attempts BETWEEN 1 AND 11)
);
ALTER TABLE studio_private.auth_rate_limits ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON studio_private.auth_rate_limits FROM PUBLIC, anon, authenticated, studio_web, studio_worker;
GRANT SELECT, INSERT, UPDATE ON studio_private.auth_rate_limits TO studio_auth_runtime;
CREATE POLICY auth_budget ON studio_private.auth_rate_limits TO studio_auth_runtime USING (true) WITH CHECK (true);
""")


def downgrade() -> None:
    raise RuntimeError("Use a forward repair migration")
