"""Import optional OAuth display data without overwriting existing profile values."""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE studio.users ADD COLUMN display_name text")
    op.execute("""
CREATE FUNCTION studio_private.provision_oauth_member(
    p_auth_user_id uuid, p_first_name text, p_last_name text, p_display_name text
) RETURNS uuid
LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $function$
DECLARE v_user_id uuid;
BEGIN
    IF length(p_first_name)>100 OR length(p_last_name)>100 OR length(p_display_name)>200 THEN
        RAISE EXCEPTION 'Invalid profile data';
    END IF;
    v_user_id := studio_private.provision_member(
        p_auth_user_id,p_first_name,p_last_name,'uk','UTC');
    UPDATE studio.users u SET
        first_name=COALESCE(u.first_name,p_first_name),
        last_name=COALESCE(u.last_name,p_last_name),
        display_name=COALESCE(u.display_name,p_display_name),
        row_version=u.row_version+1, updated_at=clock_timestamp()
    WHERE u.id=v_user_id AND u.is_active AND (
        (u.first_name IS NULL AND p_first_name IS NOT NULL) OR
        (u.last_name IS NULL AND p_last_name IS NOT NULL) OR
        (u.display_name IS NULL AND p_display_name IS NOT NULL));
    RETURN v_user_id;
END
$function$;
ALTER FUNCTION studio_private.provision_oauth_member(uuid,text,text,text) OWNER TO migration_owner;
REVOKE ALL ON FUNCTION studio_private.provision_oauth_member(uuid,text,text,text)
FROM PUBLIC, anon, authenticated, studio_web, studio_worker;
GRANT EXECUTE ON FUNCTION studio_private.provision_oauth_member(uuid,text,text,text) TO studio_auth_runtime;

DROP FUNCTION studio_private.auth_profile(uuid);
CREATE FUNCTION studio_private.auth_profile(p_user_id uuid)
RETURNS TABLE (id uuid, auth_user_id uuid, first_name text, last_name text,
    role text, locale text, timezone text, display_name text)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $function$
    SELECT u.id,u.auth_user_id,u.first_name,u.last_name,u.role,u.locale,u.timezone,u.display_name
    FROM studio.users u WHERE u.id=p_user_id AND u.is_active
$function$;
ALTER FUNCTION studio_private.auth_profile(uuid) OWNER TO migration_owner;
REVOKE ALL ON FUNCTION studio_private.auth_profile(uuid)
FROM PUBLIC, anon, authenticated, studio_web, studio_worker;
GRANT EXECUTE ON FUNCTION studio_private.auth_profile(uuid) TO studio_auth_runtime;
""")


def downgrade() -> None:
    raise RuntimeError("Use a forward repair migration; preserve imported profiles")
