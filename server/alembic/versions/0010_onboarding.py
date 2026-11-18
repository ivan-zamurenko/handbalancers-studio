"""Own questionnaire: self-report only, never an assessment (S05-01)."""

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

OWN = "user_id = NULLIF(pg_catalog.current_setting('studio.user_id', true), '')::uuid"


def upgrade() -> None:
    # CHECK cannot contain subqueries; an immutable SQL helper can.
    op.execute("""
CREATE FUNCTION studio.has_distinct_elements(anyarray) RETURNS boolean
LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
SET search_path = pg_catalog
AS $$ SELECT count(DISTINCT x) = count(*) FROM unnest($1) AS x $$
""")
    op.execute("REVOKE ALL ON FUNCTION studio.has_distinct_elements(anyarray) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION studio.has_distinct_elements(anyarray) TO studio_web")
    op.execute("""
CREATE TABLE studio.onboarding_profiles (
    user_id uuid PRIMARY KEY REFERENCES studio.users(id),
    goal_codes text[] NOT NULL,
    self_reported_level smallint NOT NULL,
    session_minutes smallint NOT NULL,
    weekdays smallint[] NOT NULL,
    time_of_day text,
    birth_year smallint,
    height_cm smallint,
    weight_kg numeric(4,1),
    completed_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT ck_onboarding_goals CHECK (
        cardinality(goal_codes) BETWEEN 1 AND 4
        AND goal_codes <@ ARRAY['handstand','strength','mobility','fitness']::text[]
        AND studio.has_distinct_elements(goal_codes)
    ),
    CONSTRAINT ck_onboarding_level CHECK (self_reported_level BETWEEN 1 AND 3),
    CONSTRAINT ck_onboarding_minutes CHECK (session_minutes IN (30, 45, 60, 90)),
    CONSTRAINT ck_onboarding_weekdays CHECK (
        cardinality(weekdays) BETWEEN 1 AND 3
        AND weekdays <@ ARRAY[1,2,3,4,5,6,7]::smallint[]
        AND studio.has_distinct_elements(weekdays)
    ),
    CONSTRAINT ck_onboarding_time CHECK (time_of_day IN ('morning', 'afternoon', 'evening')),
    CONSTRAINT ck_onboarding_birth_year CHECK (birth_year BETWEEN 1920 AND 2020),
    CONSTRAINT ck_onboarding_height CHECK (height_cm BETWEEN 100 AND 250),
    CONSTRAINT ck_onboarding_weight CHECK (weight_kg BETWEEN 25 AND 300),
    CONSTRAINT ck_onboarding_version CHECK (row_version > 0)
)
""")
    op.execute(
        "REVOKE ALL ON studio.onboarding_profiles FROM PUBLIC, anon, authenticated, "
        "studio_web, studio_auth_runtime, studio_worker"
    )
    op.execute("ALTER TABLE studio.onboarding_profiles ENABLE ROW LEVEL SECURITY")
    op.execute("GRANT SELECT, INSERT ON studio.onboarding_profiles TO studio_web")
    op.execute(
        "GRANT UPDATE (goal_codes, self_reported_level, session_minutes, weekdays, time_of_day, "
        "birth_year, height_cm, weight_kg, updated_at, row_version) "
        "ON studio.onboarding_profiles TO studio_web"
    )
    for action, clause in (
        ("SELECT", f"USING ({OWN})"),
        ("INSERT", f"WITH CHECK ({OWN})"),
        ("UPDATE", f"USING ({OWN}) WITH CHECK ({OWN})"),
    ):
        op.execute(
            f"CREATE POLICY onboarding_{action.lower()}_own ON studio.onboarding_profiles "
            f"FOR {action} TO studio_web {clause}"
        )


def downgrade() -> None:
    raise RuntimeError("Onboarding downgrade would drop answers; use a forward repair")
