# Історія платежів

S13-10: backend, local migration0016; no UI or hosted rollout.

- payments: immutable positive confirmed InvoicePayment for a card subscription.
  user/account, original invoice-line plan, invoice/subscription/customer/PaymentIntent
  identifiers, integer amount, currency, Stripe paid_at UTC, separate recorded_at, test marker.
- payment_refunds: immutable original refund facts linked to original payment,
  plus current status refreshed from Stripe under a durable lease.
  created_at is Stripe refund creation time, NOT an invented success timestamp.
  Pending/failed refunds do not reduce the paid balance; succeeded→failed restores it.
  Signed encrypted inbox events retain provider change history.
- Zero trial/no-cash invoices do not create cash payments. A reduced cash amount
  is recorded only when InvoicePayment, PaymentIntent and Charge amounts fully agree. Failed attempts remain in Checkout/inbox.
- Current supported flow: one card PaymentIntent per invoice, one invoice per PaymentIntent.
  Other/mixed-price/multi-payment/out-of-band invoices fail closed for operator review.
  This is product purchase history, not a tax/accounting ledger or dispute implementation.
- Ownership derives from local customer + durable Checkout + retrieved Stripe bindings.
  The invoice line determines the historical plan, never the current subscription plan.
- Bounded provider calls (10s timeout, no SDK retries); event lease180s permits
  the refund verification chain, customer lease60s only covers final current-state reads.
- Signed invoice.paid triggers server retrieval. History and current subscription projection
  are committed with inbox completion in one transaction. Old completed
  attempts never replace a newer current subscription.
- Refund notifications recover the original invoice payment when delivered first.
  Refund processing does not issue refunds or change entitlements.
- Payment facts permit runtime SELECT/INSERT only; refund worker can UPDATE(status) only; web reads own rows through RLS; anon/authenticated no grants.
  Immutable financial history prevents accidental user/customer deletion (restricting FKs).
- Owner GET /api/me/payments uses bounded pagination and no-store; returns amounts, times,
  plan, status and refund facts, no raw Stripe payload/customer/card data. Payment page maximum100; refund
  details maximum100 per payment with refunds_has_more; aggregate includes all successful refunds.
- Test coverage uses real isolated PostgreSQL and SDK transport contract tests.
  Actual Stripe verification and unverified rollout details belong in task evidence.

References checked 2026-11-23:
https://docs.stripe.com/api/invoice-payment/object
https://docs.stripe.com/api/invoice-payment/list
https://docs.stripe.com/api/refunds/object
https://supabase.com/docs/guides/database/postgres/row-level-security
Supabase changelog: recent CLI/branch permissions changes do not change this project's
pinned local Alembic workflow; no hosted CLI operation is used.
