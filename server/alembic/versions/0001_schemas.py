from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA studio_private")
    op.execute("REVOKE ALL ON SCHEMA studio, studio_private FROM PUBLIC")
    op.execute("GRANT USAGE ON SCHEMA studio TO studio_web, studio_auth_runtime, studio_worker")
    op.execute("GRANT USAGE ON SCHEMA studio_private TO studio_auth_runtime, studio_worker")
    op.execute("ALTER DEFAULT PRIVILEGES REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC")
    op.execute("ALTER DEFAULT PRIVILEGES REVOKE USAGE ON TYPES FROM PUBLIC")


def downgrade() -> None:
    raise RuntimeError("Baseline downgrade is disabled; use an explicit forward repair migration")