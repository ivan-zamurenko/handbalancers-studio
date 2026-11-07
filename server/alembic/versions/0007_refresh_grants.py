"""Permit fenced session refresh; no new tables, columns or identity privileges."""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
GRANT UPDATE (encrypted_tokens, access_expires_at, row_version, last_seen_at)
ON studio_private.web_sessions TO studio_auth_runtime
""")


def downgrade() -> None:
    raise RuntimeError("Refresh downgrade requires an explicit forward repair")
