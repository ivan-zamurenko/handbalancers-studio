# S13-08a — Захист від повторної підписки

Залежність S13-08. Audit P2: stale local period_end не доводить скасування у Stripe.
Nonterminal active/trialing/past_due/unpaid/paused/incomplete блокують новий
Checkout і заміну provider_subscription_id. Existing key replay зберігається.
Лише canceled/incomplete_expired дозволяють нову покупку.

Scope: checkout.py, reconciliation.py; реальні DB тести checkout_attempts
і subscription_projection. Без UI/міграцій. RED обох guard, GREEN billing suite,
read-only review, commit `fix(billing): [S13-08a] prevent duplicate subscriptions`.
Не змінює expiry правила доступу: прострочений доступ залишається закритим.
