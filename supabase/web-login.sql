-- One-time: dedicated web login for DATABASE_URL (studio_web only, under RLS).
-- Run in Supabase Dashboard -> SQL Editor AFTER `tools.migrate_cloud --apply` reached 0009.
-- Replace both CHANGE_ME with the same long random password; never commit it.
-- Supabase's postgres is not a superuser: do not list NOSUPERUSER/NOREPLICATION etc.
-- A new role already has them; the final SELECT verifies it.
BEGIN;
SET LOCAL lock_timeout = '5s';
DO $web_login$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'studio_web_app') THEN
        CREATE ROLE studio_web_app LOGIN INHERIT CONNECTION LIMIT 10 PASSWORD 'CHANGE_ME';
    ELSE
        ALTER ROLE studio_web_app WITH LOGIN PASSWORD 'CHANGE_ME';
    END IF;
END
$web_login$;
GRANT studio_web TO studio_web_app;
GRANT CONNECT ON DATABASE postgres TO studio_web_app;
COMMIT;
-- Verify: expect exactly one row  t | f | f | f | f
SELECT pg_has_role('studio_web_app', 'studio_web', 'USAGE') AS web,
       pg_has_role('studio_web_app', 'studio_auth_runtime', 'MEMBER') AS auth,
       r.rolsuper AS superuser, r.rolbypassrls AS bypass_rls, r.rolcreaterole AS createrole
FROM pg_roles r WHERE r.rolname = 'studio_web_app';
