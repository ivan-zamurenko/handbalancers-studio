BEGIN;
SET LOCAL lock_timeout = '3s';
SET LOCAL statement_timeout = '15s';

DO $$
BEGIN
    IF current_user <> 'postgres' OR current_database() <> 'postgres' THEN
        RAISE EXCEPTION 'Expected hosted postgres operator';
    END IF;
    IF EXISTS (SELECT 1 FROM auth.users WHERE id = '00000000-0000-0000-0000-000000000000') THEN
        RAISE EXCEPTION 'Probe orphan UUID must not exist';
    END IF;
END
$$;

GRANT migration_owner TO postgres WITH INHERIT TRUE, SET TRUE;
SET LOCAL ROLE migration_owner;
CREATE SCHEMA studio_fk_probe_20261021 AUTHORIZATION migration_owner;
CREATE TABLE studio_fk_probe_20261021.profiles (auth_user_id uuid NOT NULL);
ALTER TABLE studio_fk_probe_20261021.profiles ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON studio_fk_probe_20261021.profiles FROM PUBLIC;

DO $$
BEGIN
    BEGIN
        ALTER TABLE studio_fk_probe_20261021.profiles
            ADD CONSTRAINT probe_auth_fk FOREIGN KEY (auth_user_id) REFERENCES auth.users(id);
        RAISE EXCEPTION 'Expected migration_owner FK creation to fail';
    EXCEPTION WHEN insufficient_privilege THEN
        NULL;
    END;
END
$$;

RESET ROLE;
ALTER TABLE studio_fk_probe_20261021.profiles
    ADD CONSTRAINT probe_auth_fk FOREIGN KEY (auth_user_id) REFERENCES auth.users(id);

DO $$
BEGIN
    IF has_schema_privilege('migration_owner', 'auth', 'USAGE')
        OR has_column_privilege('migration_owner', 'auth.users', 'id', 'REFERENCES') THEN
        RAISE EXCEPTION 'Migration role unexpectedly acquired Auth privileges';
    END IF;
END
$$;

SET LOCAL ROLE migration_owner;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = 'studio_fk_probe_20261021.profiles'::regclass
            AND relowner = 'migration_owner'::regrole
    ) THEN
        RAISE EXCEPTION 'Table owner changed';
    END IF;
    BEGIN
        INSERT INTO studio_fk_probe_20261021.profiles (auth_user_id)
            VALUES ('00000000-0000-0000-0000-000000000000');
        RAISE EXCEPTION 'Expected foreign key rejection';
    EXCEPTION WHEN foreign_key_violation THEN
        NULL;
    END;
END
$$;
RESET ROLE;
ROLLBACK;

SELECT current_user,
    NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'studio_fk_probe_20261021') AS probe_schema_absent,
    NOT pg_has_role('postgres', 'migration_owner', 'SET') AS operator_set_restored,
    NOT pg_has_role('postgres', 'migration_owner', 'USAGE') AS operator_inherit_restored,
    NOT has_schema_privilege('migration_owner', 'auth', 'USAGE') AS migration_auth_usage_absent,
    NOT has_column_privilege('migration_owner', 'auth.users', 'id', 'REFERENCES') AS migration_auth_references_absent;