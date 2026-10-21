"""Minimal profiles linked to managed Auth identities."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("auth_user_id", sa.Uuid(), nullable=False),
        sa.Column("first_name", sa.Text(), nullable=True),
        sa.Column("last_name", sa.Text(), nullable=True),
        sa.Column("role", sa.Text(), server_default=sa.text("'member'"), nullable=False),
        sa.Column("locale", sa.Text(), nullable=False),
        sa.Column("timezone", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("row_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("auth_user_id", name="uq_users_auth_user_id"),
        sa.ForeignKeyConstraint(["auth_user_id"], ["auth.users.id"], name="fk_users_auth_user_id"),
        sa.CheckConstraint("role IN ('member', 'coach')", name="ck_users_role"),
        sa.CheckConstraint("locale IN ('uk', 'en')", name="ck_users_locale"),
        sa.CheckConstraint("row_version > 0", name="ck_users_row_version"),
        schema="studio",
    )
    # Fail closed until explicit policies and column grants arrive in S01-05.
    op.execute("ALTER TABLE studio.users ENABLE ROW LEVEL SECURITY")
    op.execute(
        "REVOKE ALL ON studio.users FROM PUBLIC, studio_web, studio_auth_runtime, studio_worker"
    )


def downgrade() -> None:
    raise RuntimeError("Profile downgrade is disabled; use an explicit forward repair migration")
