"""Verified profiles, selected plans and durable training history."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002_accounts_and_progress"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    for name, kind in [
        ("first_name", sa.String(100)),
        ("last_name", sa.String(100)),
        ("password_hash", sa.String(256)),
        ("email_verified_at", sa.DateTime(timezone=True)),
        ("trial_used_at", sa.DateTime(timezone=True)),
    ]:
        op.add_column("users", sa.Column(name, kind))
    op.execute("UPDATE users SET first_name = name")
    # Do not silently merge users if historical OAuth identities share an email.
    op.create_index(
        "uq_users_verified_email",
        "users",
        [sa.text("lower(email)")],
        unique=True,
        postgresql_where=sa.text("NOT is_demo AND email IS NOT NULL"),
    )
    op.add_column("browser_sessions", sa.Column("selected_plan", sa.String(16)))
    op.add_column(
        "checkout_attempts",
        sa.Column("trial_days", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "subscriptions",
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "email_verifications",
        sa.Column(
            "session_hash",
            sa.String(64),
            sa.ForeignKey("browser_sessions.token_hash", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(256), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
    )
    op.create_table(
        "auth_rate_limits",
        sa.Column("key_hash", sa.String(64), primary_key=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
    )
    op.create_table(
        "training_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scheduled_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("actual_minutes", sa.Integer()),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("goal", sa.String(16)),
        sa.Column("status", sa.String(16), nullable=False),
        sa.CheckConstraint(
            "actual_minutes IS NULL OR actual_minutes BETWEEN 1 AND 480", name="ck_training_minutes"
        ),
    )
    op.create_index("ix_training_sessions_user_id", "training_sessions", ["user_id"])
    op.create_index("ix_training_sessions_completed_at", "training_sessions", ["completed_at"])


def downgrade():
    for table in ["training_sessions", "auth_rate_limits", "email_verifications"]:
        op.drop_table(table)
    op.drop_column("subscriptions", "cancel_at_period_end")
    op.drop_column("checkout_attempts", "trial_days")
    op.drop_column("browser_sessions", "selected_plan")
    op.drop_index("uq_users_verified_email", table_name="users")
    for name in ["trial_used_at", "email_verified_at", "password_hash", "last_name", "first_name"]:
        op.drop_column("users", name)
