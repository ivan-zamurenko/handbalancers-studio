# Stripe test-mode roundtrip

Use only the dedicated local Supabase test stack. The runner verifies that
boundary before creating Stripe objects. It reads `test_mode_api_key` from the
local Stripe CLI profile; never paste keys into commands or chat.

```sh
PATH="$PWD/.local-tools/supabase-cli/node_modules/@supabase/cli-darwin-arm64/bin:$PATH" \
DOCKER_HOST="unix://$HOME/.colima/studio-s01/docker.sock" \
.venv/bin/python tools/local_stack.py test .venv/bin/python -m tools.stripe_testmode
```

The runner creates a separately labelled test catalog (four exact EUR monthly
prices), disposable local members, a test-clock customer, local HTTP server8787,
CLI forwarding and the actual reconciler. No subscriptions/entitlements are
seeded. Auth/JWT/mail/DB and Stripe are real. DB transactions use narrow roles
through the isolated-test helper; hosted credentials/topology are not tested.

When `ready`, in another terminal:

```sh
PATH="$PWD/.local-tools/node-v24.21.0-darwin-arm64/bin:$PATH" \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.local-tools/playwright-browsers" \
node tools/stripe_testmode_browser.mjs pro
# Repeat with plus instead of pro.
```

Only published TEST card data enters Stripe-hosted frames. Pro first tests a
decline with no subscription, then a successful payment. Plus starts a seven-day
card-backed trial. Both await confirmed server projection and a loaded Portal.
No request interception or mocked provider responses. `--portal-only` reopens an
already verified purchase's Portal; `--inspect` stops before submission.
`--self-check` rejects five unsafe fixture/URL/run-ID cases without a network.

In the runner terminal, one command at a time:

1. `audit`: actual invoices, owner isolation, strict payloads, duplicate purchase,
   CSRF/Origin, invalid signature, real CLI delivery and duplicate inbox.
2. `advance`: Plus clock beyond seven days and invoice finalization; verify paid
   €49.99 invoice and active local projection.
3. `cancel`: cancel only this run's synthetic subscriptions; await projections.
4. `stop`: stop services and remove the browser cookie fixture.

Pass requires all checks, same-run loaded browser results and cleanup. Pending
or failed runs exit nonzero. A new run invalidates old results; failures persist.
Browser outputs bind the initial run ID and reject drift. Artifacts remain in
ignored `private-evidence/stripe-testmode`, directory0700, sensitive files0600.
Never commit cookies, Checkout/Portal URLs, signing secrets or raw payloads.

Duplicates replay immediately over HTTP with the original CLI body/signature.
For Pro, external proof is two200 responses, one inbox row and initial projection version1.
Replay after completed processing is a separate real PostgreSQL regression;
this external gate does not claim that timing guarantee.

Official references: [test cards](https://docs.stripe.com/testing),
[billing lifecycle](https://docs.stripe.com/billing/testing),
[Checkout API](https://docs.stripe.com/api/checkout/sessions/create).
Pinned2026-11-18.endive uses `allowed_payment_method_types: ["card"]`.
The removed `payment_method_types` was rejected by Stripe and fixed in S13-09a.

This gate authorizes no live charges, hosted migrations, deployment or sale.
