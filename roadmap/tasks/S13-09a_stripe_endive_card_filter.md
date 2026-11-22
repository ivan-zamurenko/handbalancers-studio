# S13-09a — Stripe Endive card filter

Dependency08a. Actual Stripe400 rejects payment_method_types in pinned API2026-11-18.endive.
Official API now uses allowed_payment_method_types as a filter of eligible methods.
Scope gateway +SDK transport test. Keep only card, trial card collection, exact prices.
RED missing wire field; GREEN billing SDK suite; independent review. No UI/DB changes.
Source https://docs.stripe.com/api/checkout/sessions/create (2026-11-22).
Commit `fix(billing): [S13-09a] use supported card payment filter`.
