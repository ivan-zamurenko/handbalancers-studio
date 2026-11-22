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

## Local test runtime (S13-02)

`BILLING_ENABLED=false` by default. Enabling requires a local/test APP_ENV,
PUBLIC_ORIGIN, DATABASE_URL for studio_web, WORKER_DATABASE_URL for a dedicated
studio_worker login, STRIPE_SECRET_KEY (test-only), STRIPE_WEBHOOK_SECRET and
STRIPE_PRICE_ESSENTIAL/PLUS/PRO/PRO_PLUS. Configure through the private environment;
never source unreviewed archived shell files. App construction performs no network I/O.

POST `/api/checkout` accepts only `{plan_code, terms_version:"test-v1"}` with a
trusted session, same Origin, session CSRF and Idempotency-Key (1–128 chars).
The saved questionnaire and names must be complete. Test-v1 is a sandbox consent
marker, not approved production legal terms. GET `/api/me/checkout-attempts/{id}`
returns only an owned attempt. Neither redirect nor GET grants entitlement.

Each attempt is committed before contacting Stripe. A retry retains its original
attempt/key and two-hour expiry; ambiguous attempts within 30 minutes of expiry
need provider reconciliation rather than a new checkout. Customer mapping uses
a stable per-user Stripe idempotency key; PostgreSQL verifies unique binding.
Worker role may create customer bindings and manage checkout attempts, but web,
auth and direct Supabase client roles cannot issue them. Subscription writes are
still closed until the signed-event reconciliation implementation.

## Webhook ingress (S13-03)

POST `/api/webhooks/stripe` requires one Stripe-Signature header over the original
raw body, with a timestamp within ±300 seconds. Only test events from this account
are accepted; Connect/account events and live-mode objects are rejected. The usual
64 KiB request bound remains. This endpoint alone uses the provider signature
instead of browser Origin/CSRF; it cannot issue browser commands.

The response is200 only after commit to `studio_private.webhook_events`; DB failure
returns503 for Stripe retry. Event IDs are unique. Raw payload is encrypted with
AES-256-GCM and event-ID-associated data using the configured TOKEN_ENCRYPTION_KEY.
Only studio_worker can read/write the inbox; public/web/auth roles cannot read it.
Unsupported event types are recorded as ignored; supported references wait for the
reconciliation worker. Neither webhook body metadata nor event time directly grants
access. Payloads and SDK responses must never enter logs.

## Reconciliation worker (S13-04)

Run `python -m studio.jobs.billing_worker --watch` under the same private test
environment. Without --watch it handles at most10 events and exits. A tick also
schedules at most10 known pending sessions, once per five-minute bucket; failed
events are not silently requeued. Inspect failed event state with a trusted operator.
No live environment is supported.

Events lease for90s; customer reconciliation leases for60s. Stripe is re-read after
the durable customer lease, outside any DB transaction. Both lease tokens and
expiry fence the atomic projection/attempt/event commit. Event timestamps do not
order subscription rights. Same-state delivery does not bump row_version.
Failures retry after30s, at most5 attempts; crashes leave recoverable lease state.
A fresh subscription must match an owned durable Checkout and local customer
binding; metadata alone is insufficient. Current invoice must be paid for active
access; trial/card constraints are checked independently. Unknown or mismatched
provider data grants nothing. Non-subscription invoices are ignored safely.

Migration0014 adds customer lease columns and grants only the trusted worker
INSERT/UPDATE subscription rights. Public/web/auth clients cannot issue rights.
The hosted migration runner remains pinned to0010 pending separate authorization.
