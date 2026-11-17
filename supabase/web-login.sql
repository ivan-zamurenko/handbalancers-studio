-- One-time: dedicated web login for DATABASE_URL (studio_web only, under RLS).
-- Run in Supabase Dashboard -> SQL Editor AFTER `tools.migrate_cloud --apply` reached 0009.
-- Replace CHANGE_ME with a long random password (password manager); never commit it.
BEGIN;
SET LOCAL lock_timeout = '5s';
DO $web_login$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'studio_web_app') THEN
        CREATE ROLE studio_web_app;
    END IF;
END
$web_login$;
ALTER ROLE studio_web_app LOGIN INHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE
    NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 10 PASSWORD 'CHANGE_ME';
GRANT studio_web TO studio_web_app;
GRANT CONNECT ON DATABASE postgres TO studio_web_app;
-- Verify: expect one row "t | f | f".
SELECT pg_has_role('studio_web_app', 'studio_web', 'USAGE') AS web,
       pg_has_role('studio_web_app', 'studio_auth_runtime', 'MEMBER') AS auth,
       r.rolbypassrls AS bypass_rls
FROM pg_roles r WHERE r.rolname = 'studio_web_app';
COMMIT;
