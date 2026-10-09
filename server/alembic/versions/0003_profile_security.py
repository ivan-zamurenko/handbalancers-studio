"""Own active profiles and a narrow trusted-auth provisioning boundary."""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("REVOKE ALL ON SCHEMA studio, studio_private FROM PUBLIC, anon, authenticated")
    op.execute(
        "REVOKE ALL ON studio.users FROM PUBLIC, anon, authenticated, "
        "studio_web, studio_auth_runtime, studio_worker"
    )
    op.execute("ALTER TABLE studio.users ENABLE ROW LEVEL SECURITY")
    op.execute("""
CREATE POLICY users_select_own ON studio.users FOR SELECT TO studio_web
USING (
    is_active AND id = NULLIF(pg_catalog.current_setting('studio.user_id', true), '')::uuid
)
""")
    op.execute("""
CREATE POLICY users_update_own ON studio.users FOR UPDATE TO studio_web
USING (
    is_active AND id = NULLIF(pg_catalog.current_setting('studio.user_id', true), '')::uuid
)
WITH CHECK (
    is_active AND id = NULLIF(pg_catalog.current_setting('studio.user_id', true), '')::uuid
)
""")
    op.execute("GRANT SELECT ON studio.users TO studio_web")
    op.execute(
        "GRANT UPDATE (first_name, last_name, locale, timezone) ON studio.users TO studio_web"
    )
    # The auth service must verify provider identity before calling. No role,
    # is_active or metadata arguments; retries preserve every existing attribute.
    op.execute("""
CREATE FUNCTION studio_private.provision_member(
    p_auth_user_id uuid, p_first_name text, p_last_name text,
    p_locale text, p_timezone text
) RETURNS uuid
LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $function$
DECLARE
    v_user_id uuid;
BEGIN
    INSERT INTO studio.users (auth_user_id, first_name, last_name, locale, timezone, role)
    VALUES (p_auth_user_id, p_first_name, p_last_name, p_locale, p_timezone, 'member')
    ON CONFLICT (auth_user_id) DO NOTHING;

    -- Separate command snapshot sees a concurrent committed insert at READ COMMITTED.
    SELECT id INTO STRICT v_user_id FROM studio.users WHERE auth_user_id = p_auth_user_id;
    RETURN v_user_id;
END
$function$
""")
    op.execute("""
ALTER FUNCTION studio_private.provision_member(uuid,text,text,text,text)
OWNER TO migration_owner
""")
    op.execute("""
REVOKE ALL ON FUNCTION studio_private.provision_member(uuid,text,text,text,text)
FROM PUBLIC, anon, authenticated, studio_web, studio_worker
""")
    op.execute("""
GRANT EXECUTE ON FUNCTION studio_private.provision_member(uuid,text,text,text,text)
TO studio_auth_runtime
""")


def downgrade() -> None:
    raise RuntimeError(
        "Profile security downgrade is disabled; use an explicit forward repair migration"
    )
