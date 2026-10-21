-- One-time registration database setup. Run directly in Supabase SQL Editor/MCP.
-- This intentionally does not write to supabase_migrations.schema_migrations.

BEGIN;

CREATE SCHEMA studio AUTHORIZATION postgres;
CREATE SCHEMA studio_private AUTHORIZATION postgres;

REVOKE ALL ON SCHEMA studio, studio_private FROM PUBLIC, anon, authenticated;
GRANT USAGE ON SCHEMA studio TO studio_web, studio_auth_runtime, studio_worker;
GRANT USAGE ON SCHEMA studio_private TO studio_auth_runtime, studio_worker;

CREATE TABLE studio.users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_user_id uuid NOT NULL,
    first_name text,
    last_name text,
    display_name text,
    role text NOT NULL DEFAULT 'member',
    locale text NOT NULL,
    timezone text NOT NULL,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT uq_users_auth_user_id UNIQUE (auth_user_id),
    CONSTRAINT fk_users_auth_user_id FOREIGN KEY (auth_user_id) REFERENCES auth.users(id),
    CONSTRAINT ck_users_role CHECK (role IN ('member', 'coach')),
    CONSTRAINT ck_users_locale CHECK (locale IN ('uk', 'en')),
    CONSTRAINT ck_users_row_version CHECK (row_version > 0)
);

ALTER TABLE studio.users ENABLE ROW LEVEL SECURITY;
CREATE POLICY users_select_own ON studio.users FOR SELECT TO studio_web
USING (
    is_active AND id = NULLIF(pg_catalog.current_setting('studio.user_id', true), '')::uuid
);
CREATE POLICY users_update_own ON studio.users FOR UPDATE TO studio_web
USING (
    is_active AND id = NULLIF(pg_catalog.current_setting('studio.user_id', true), '')::uuid
)
WITH CHECK (
    is_active AND id = NULLIF(pg_catalog.current_setting('studio.user_id', true), '')::uuid
);
REVOKE ALL ON studio.users FROM PUBLIC, anon, authenticated,
    studio_web, studio_auth_runtime, studio_worker;
GRANT SELECT ON studio.users TO studio_web;
GRANT UPDATE (first_name, last_name, locale, timezone) ON studio.users TO studio_web;

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

    SELECT id INTO STRICT v_user_id FROM studio.users WHERE auth_user_id = p_auth_user_id;
    RETURN v_user_id;
END
$function$;
REVOKE ALL ON FUNCTION studio_private.provision_member(uuid,text,text,text,text)
    FROM PUBLIC, anon, authenticated, studio_web, studio_worker;
GRANT EXECUTE ON FUNCTION studio_private.provision_member(uuid,text,text,text,text)
    TO studio_auth_runtime;

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
);
CREATE INDEX ix_studio_private_web_sessions_user_id ON studio_private.web_sessions(user_id);
ALTER TABLE studio_private.web_sessions ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON studio_private.web_sessions FROM PUBLIC, anon, authenticated,
    studio_web, studio_worker, studio_auth_runtime;
GRANT SELECT, INSERT ON studio_private.web_sessions TO studio_auth_runtime;
GRANT UPDATE (revoked_at) ON studio_private.web_sessions TO studio_auth_runtime;
CREATE POLICY auth_read ON studio_private.web_sessions
    FOR SELECT TO studio_auth_runtime USING (true);
CREATE POLICY auth_insert ON studio_private.web_sessions
    FOR INSERT TO studio_auth_runtime WITH CHECK (true);
CREATE POLICY auth_update ON studio_private.web_sessions
    FOR UPDATE TO studio_auth_runtime USING (true) WITH CHECK (true);

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
);
CREATE INDEX ix_studio_private_auth_attempts_user_id ON studio_private.auth_attempts(user_id);
ALTER TABLE studio_private.auth_attempts ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON studio_private.auth_attempts FROM PUBLIC, anon, authenticated,
    studio_web, studio_worker, studio_auth_runtime;
GRANT SELECT, INSERT ON studio_private.auth_attempts TO studio_auth_runtime;
GRANT UPDATE (consumed_at) ON studio_private.auth_attempts TO studio_auth_runtime;
CREATE POLICY auth_read ON studio_private.auth_attempts
    FOR SELECT TO studio_auth_runtime USING (true);
CREATE POLICY auth_insert ON studio_private.auth_attempts
    FOR INSERT TO studio_auth_runtime WITH CHECK (true);
CREATE POLICY auth_update ON studio_private.auth_attempts
    FOR UPDATE TO studio_auth_runtime USING (true) WITH CHECK (true);

CREATE TABLE studio_private.auth_rate_limits (
    bucket_hash text PRIMARY KEY,
    window_start timestamptz NOT NULL,
    attempts integer NOT NULL CHECK (attempts BETWEEN 1 AND 11)
);
ALTER TABLE studio_private.auth_rate_limits ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON studio_private.auth_rate_limits FROM PUBLIC, anon, authenticated,
    studio_web, studio_worker;
GRANT SELECT, INSERT, UPDATE ON studio_private.auth_rate_limits TO studio_auth_runtime;
CREATE POLICY auth_budget ON studio_private.auth_rate_limits TO studio_auth_runtime
    USING (true) WITH CHECK (true);

CREATE FUNCTION studio_private.provision_oauth_member(
    p_auth_user_id uuid, p_first_name text, p_last_name text, p_display_name text
) RETURNS uuid
LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $function$
DECLARE
    v_user_id uuid;
BEGIN
    IF length(p_first_name) > 100 OR length(p_last_name) > 100
       OR length(p_display_name) > 200 THEN
        RAISE EXCEPTION 'Invalid profile data';
    END IF;
    v_user_id := studio_private.provision_member(
        p_auth_user_id, p_first_name, p_last_name, 'uk', 'UTC'
    );
    UPDATE studio.users u SET
        first_name = COALESCE(u.first_name, p_first_name),
        last_name = COALESCE(u.last_name, p_last_name),
        display_name = COALESCE(u.display_name, p_display_name),
        row_version = u.row_version + 1,
        updated_at = clock_timestamp()
    WHERE u.id = v_user_id AND u.is_active AND (
        (u.first_name IS NULL AND p_first_name IS NOT NULL) OR
        (u.last_name IS NULL AND p_last_name IS NOT NULL) OR
        (u.display_name IS NULL AND p_display_name IS NOT NULL)
    );
    RETURN v_user_id;
END
$function$;
REVOKE ALL ON FUNCTION studio_private.provision_oauth_member(uuid,text,text,text)
    FROM PUBLIC, anon, authenticated, studio_web, studio_worker;
GRANT EXECUTE ON FUNCTION studio_private.provision_oauth_member(uuid,text,text,text)
    TO studio_auth_runtime;

CREATE FUNCTION studio_private.auth_profile(p_user_id uuid)
RETURNS TABLE (
    id uuid, auth_user_id uuid, first_name text, last_name text,
    role text, locale text, timezone text, display_name text
)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $function$
    SELECT u.id, u.auth_user_id, u.first_name, u.last_name, u.role,
           u.locale, u.timezone, u.display_name
    FROM studio.users u WHERE u.id = p_user_id AND u.is_active
$function$;
REVOKE ALL ON FUNCTION studio_private.auth_profile(uuid)
    FROM PUBLIC, anon, authenticated, studio_web, studio_worker;
GRANT EXECUTE ON FUNCTION studio_private.auth_profile(uuid) TO studio_auth_runtime;

COMMIT;