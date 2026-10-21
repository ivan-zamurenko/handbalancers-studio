"""Fail-closed catalogue checks for adopting the reviewed registration bootstrap.

Fingerprints are generated from real PostgreSQL DDL, not from live customer data.
Integration tests bind them to both the immutable migrations and bootstrap SQL.
Column physical order is intentionally irrelevant; SQL bodies are compared exactly.
"""

import hashlib
import json
from pathlib import Path

from sqlalchemy import Connection, text

from tools.check_migrations import require

MANIFEST = Path(__file__).with_name("registration_baseline_0006.json")
SCHEMAS = "('studio','studio_private')"
# Ignore only Alembic's own bookkeeping objects, including its backing index/type.
RELATIONS = "c.relname NOT IN ('alembic_version','alembic_version_pkc')"
QUERIES = {
    "schemas": f"""
        SELECT nspname,pg_get_userbyid(nspowner) FROM pg_namespace
        WHERE nspname IN {SCHEMAS} ORDER BY 1
    """,
    "relations": f"""
        SELECT n.nspname,c.relname,c.relkind,pg_get_userbyid(c.relowner),
               c.relrowsecurity,c.relforcerowsecurity,c.relpersistence,c.reloptions
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname IN {SCHEMAS} AND {RELATIONS} ORDER BY 1,2
    """,
    "columns": f"""
        SELECT n.nspname,c.relname,a.attname,format_type(a.atttypid,a.atttypmod),
               a.attnotnull,a.attidentity,a.attgenerated,
               pg_get_expr(d.adbin,d.adrelid),co.collname
        FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
        JOIN pg_namespace n ON n.oid=c.relnamespace
        LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum
        LEFT JOIN pg_collation co ON co.oid=a.attcollation
        WHERE n.nspname IN {SCHEMAS} AND {RELATIONS} AND c.relkind IN ('r','p','v','m')
              AND a.attnum>0 AND NOT a.attisdropped ORDER BY 1,2,3
    """,
    "constraints": f"""
        SELECT n.nspname,c.relname,k.conname,k.convalidated,pg_get_constraintdef(k.oid)
        FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid
        JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname IN {SCHEMAS} AND {RELATIONS} ORDER BY 1,2,3
    """,
    "indexes": """
        SELECT schemaname,tablename,indexname,indexdef FROM pg_indexes
        WHERE schemaname IN ('studio','studio_private') AND tablename <> 'alembic_version'
        ORDER BY 1,2,3
    """,
    "policies": """
        SELECT schemaname,tablename,policyname,permissive,roles::text,cmd,qual,with_check
        FROM pg_policies WHERE schemaname IN ('studio','studio_private') ORDER BY 1,2,3
    """,
    "functions": f"""
        SELECT n.nspname,p.proname,pg_get_function_identity_arguments(p.oid),
               pg_get_userbyid(p.proowner),pg_get_functiondef(p.oid)
        FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
        WHERE n.nspname IN {SCHEMAS} ORDER BY 1,2,3
    """,
    "triggers": f"""
        SELECT n.nspname,c.relname,t.tgname,t.tgenabled,pg_get_triggerdef(t.oid)
        FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
        JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname IN {SCHEMAS} AND NOT t.tgisinternal ORDER BY 1,2,3
    """,
    "rules": f"""
        SELECT n.nspname,c.relname,r.rulename,pg_get_ruledef(r.oid)
        FROM pg_rewrite r JOIN pg_class c ON c.oid=r.ev_class
        JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname IN {SCHEMAS} ORDER BY 1,2,3
    """,
    "grants": f"""
        WITH objects AS (
          SELECT 'schema' AS kind,n.nspname AS name,
                 coalesce(n.nspacl,acldefault('n',n.nspowner)) AS acl
          FROM pg_namespace n WHERE n.nspname IN {SCHEMAS}
          UNION ALL
          SELECT 'table',n.nspname||'.'||c.relname,
                 coalesce(c.relacl,acldefault('r',c.relowner))
          FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
          WHERE n.nspname IN {SCHEMAS} AND {RELATIONS} AND c.relkind IN ('r','p','v','m')
          UNION ALL
          SELECT 'column',n.nspname||'.'||c.relname||'.'||a.attname,a.attacl
          FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
          JOIN pg_namespace n ON n.oid=c.relnamespace
          WHERE n.nspname IN {SCHEMAS} AND {RELATIONS} AND a.attnum>0
          UNION ALL
          SELECT 'function',p.oid::regprocedure::text,
                 coalesce(p.proacl,acldefault('f',p.proowner))
          FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
          WHERE n.nspname IN {SCHEMAS}
        )
        SELECT kind,name,pg_get_userbyid(x.grantor),
               CASE WHEN x.grantee=0 THEN 'PUBLIC' ELSE pg_get_userbyid(x.grantee) END,
               x.privilege_type,x.is_grantable
        FROM objects CROSS JOIN LATERAL aclexplode(acl) x ORDER BY 1,2,3,4,5,6
    """,
}


def catalogue_fingerprints(connection: Connection) -> dict[str, str]:
    previous = connection.scalar(text("SHOW search_path"))
    connection.execute(text("SELECT set_config('search_path','pg_catalog,pg_temp',true)"))
    try:
        return {
            name: hashlib.sha256(json.dumps(
                [list(row) for row in connection.execute(text(query))],
                separators=(",", ":"),
            ).encode()).hexdigest()
            for name, query in QUERIES.items()
        }
    finally:
        connection.execute(text("SELECT set_config('search_path',:path,true)"), {"path": previous})


def verify_registration_baseline(connection: Connection) -> None:
    expected = json.loads(MANIFEST.read_text())
    actual = catalogue_fingerprints(connection)
    mismatches = [name for name, value in actual.items() if value not in expected[name]]
    require(not mismatches, "Registration baseline differs: " + ", ".join(mismatches))


def reconcile_default_privileges(connection: Connection) -> None:
    # Exactly the missing effects of 0001; existing objects/data are untouched.
    connection.exec_driver_sql("ALTER DEFAULT PRIVILEGES REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC")
    connection.exec_driver_sql("ALTER DEFAULT PRIVILEGES REVOKE USAGE ON TYPES FROM PUBLIC")
