"""Fence current-provider reads without long DB locks (S13-04)."""

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE studio.billing_customers ADD COLUMN reconcile_token uuid, ADD COLUMN reconcile_until timestamptz"
    )
    op.execute(
        "GRANT UPDATE(reconcile_token,reconcile_until) ON studio.billing_customers TO studio_worker"
    )
    op.execute(
        "CREATE POLICY customer_billing_lease ON studio.billing_customers FOR UPDATE TO studio_worker USING(true) WITH CHECK(true)"
    )
    op.execute("GRANT INSERT,UPDATE ON studio.subscriptions TO studio_worker")
    op.execute(
        "CREATE POLICY subscription_billing_insert ON studio.subscriptions FOR INSERT TO studio_worker WITH CHECK(true)"
    )
    op.execute(
        "CREATE POLICY subscription_billing_update ON studio.subscriptions FOR UPDATE TO studio_worker USING(true) WITH CHECK(true)"
    )


def downgrade() -> None:
    raise RuntimeError("Billing reconciliation downgrade requires a forward repair")
