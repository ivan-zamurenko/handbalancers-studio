# S13-10 — Payment history

Підтверджені Stripe платежі з власником, пакетом, сумою та UTC часом незалежно від поточної підписки.

- confirmed_history: Verified invoice payment recorded once; UTC paid time and original plan preserved.
- ownership_and_immutability: Owner-only RLS, runtime no financial-fact UPDATE/DELETE (worker UPDATE refund status only), foreign bindings fail closed.
- atomic_replay: Duplicate/concurrent deliveries do not duplicate; lease failure rolls back history and current projection.
- refund_history: Verified refund facts and current status separate; failed refund restores balance; out-of-order refund recovers payment; no excess refund.
- safe_read: Authenticated bounded owner-only API, no-store, no sensitive provider payload.

GET /api/me/payments, bounded pagination. No UI.
0016 payments/payment_refunds, append-only runtime grants and owner RLS. Local only.

Commit: feat(billing): [S13-10] preserve payment and refund history
