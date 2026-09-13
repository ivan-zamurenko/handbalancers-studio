-- Executed only while initializing an empty PostgreSQL volume.
-- psql obtains the value from the container environment; no password in SQL/Git.
\getenv app_password APP_DATABASE_PASSWORD
CREATE ROLE studio LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD :'app_password';
CREATE DATABASE studio OWNER studio;
\connect studio
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
ALTER SCHEMA public OWNER TO studio;
