# Stripe test-mode setup

Owner authorized test payments and prioritized Stripe on 2026-11-22.
New runtime uses stripe-python 17.1.0, API 2026-11-18.endive. No live-mode
credentials or objects are accepted. SDK HTTP timeout is 10 seconds with no
implicit network retries; durable Checkout retry belongs to the service.

Use the existing Stripe account. CLI authorization is at
`~/.config/stripe/config.toml`; never print or commit its contents. The saved
test credential returned AuthenticationError/401 on 2026-11-22. Refresh it with
`stripe login`, not by pasting keys into chat. Live credentials must not be used.

The server maps `essential`, `plus`, `pro`, `pro-plus` to configured Price IDs.
Each Price must be active, test-mode, EUR/month, licensed/per-unit, quantity one,
with amounts 1999/4999/17999/29999 minor units. Validate with
`StripeGateway.validate_catalog()` before enabling Checkout; each create also
revalidates its selected Price. Clients cannot submit a Price ID or amount.

Archived reference: tag `archive/pre-execution-v4`, `server/studio/billing.py`.
Do not restore its runtime, demo access, old auth, or network calls under DB locks.

Sources: [Stripe Checkout](https://docs.stripe.com/api/checkout/sessions/create),
[Stripe webhook handling](https://docs.stripe.com/webhooks),
[SDK/API pin](https://github.com/stripe/stripe-python/blob/v17.1.0/stripe/_api_version.py).
