# S13-09 — actual Stripe TEST verification, 2026-11-22

Result: **external_verified for test payments only**. Real Stripe sandbox,
CLI forwarding and local isolated Supabase/Auth/PostgreSQL. No production data,
live money, hosted migration or deployment changed. The final runner exited0
with statuspassed and no failed checks; private evidence is ignored by Git.

| Scenario | Observed result |
| --- | --- |
| Pro declined card | Stripe displayed decline; local subscription remained absent |
| Pro successful card | Hosted Checkout completed; actual invoice paid17999EUR cents; signed webhook produced active Pro |
| Plus trial | Hosted card Checkout, paid0EUR invoice, seven-day trial, stored card; server trialing projection |
| End of trial | Actual Test Clock advanced beyond trial and finalization; paid4999EUR cents, server active projection |
| Billing Portal | Actual owned Portal loaded for Pro and Plus; subscription/card/invoice information visible |
| Signed events | Final run accepted14 signed HTTP deliveries: CLI events and their local replays; invalid signature400 |
| Duplicate delivery | Pro Checkout: two replay HTTP200 responses, one inbox row for that event, initial row_version1 |
| Isolation | Different authenticated member sees no subscription; foreign attempt404 |
| Tampering | Extra price_id/trial/user_id rejected422; new Checkout with existing subscription409 |
| Session protection | Invalid CSRF403 and foreign Origin403 |
| Test-only guard | Two live keys with otherwise-valid catalog and live object rejected; browser rejects five unsafe local/URL/run fixtures |
| Cleanup | Both synthetic subscriptions canceled in Stripe and projected canceled; local services stopped |

Card details were entered in Stripe frames. App API receives only the selected
plan, terms version, session protection and idempotency key. The test runner
uses synthetic identities; no owner's card or account was charged.

Personally viewed actual provider pages and app confirmation/active states for
Pro and Plus, declined-card page and fully loaded Portals. UI layout coverage
320/390/1440, both themes and UA/EN is recorded separately in S13-08.

The durable duplicate test does not claim replay occurred after processing.
`test_repeated_projection_idempotent` on real local PostgreSQL separately checks
repeating a projection from a subsequent event with a different event ID. Neither
case is reported as same-event replay after processing. Global inbox counts also
include earlier diagnostic runs, not only events from the final run.

Issues found and fixed:

- Audit found expired local period_end could allow duplicate subscriptions;
  S13-08a now requires a terminal old subscription before new purchase/replacement.
- Actual Stripe rejected the removed payment_method_types parameter.
  S13-09a uses the pinned API's supported card-only filter.
- Runner diagnostics corrected iframe selectors, readonly email and waiting for
  Portal content. A first run's HTTP-client context error was recorded as failed;
  its subscriptions were canceled, then the corrected runner passed a fresh run.
- Independent review tightened test-only browser guards, failure evidence,
  captured run-ID binding and the scope of duplicate-delivery claims.

Limits: this is not a comprehensive penetration test or a promise of immunity
from attacks. Hosted deployment, real payments, tax/commerce approval and
unimplemented plan/AI/coach readiness remain separate. Essential/Pro+ catalog
values were validated against real Stripe; browser purchases exercised Pro/Plus.

## Concrete next step for the owner's existing app

The current `.env.local` targets the existing hosted database and has no Stripe
or worker-login configuration. The guarded cloud runner still authorizes only
revision0010. Its actual cloud head was not rechecked in this gate.

To make test purchase available in that app, separately approve applying the
already locally tested migrations0011–0015 to the existing project:

- 0011: customer/subscription projection and owner read isolation.
- 0012: durable Checkout attempts and narrow worker writes.
- 0013: encrypted private webhook inbox.
- 0014: reconciliation leases and projection writer grants.
- 0015: one-trial claim history and immutable confirmed claim protection.

After that approval, update and verify the explicit cloud migration allowance,
inspect the actual target revision, apply the five migrations using the guarded
transactional runner, provision a separate narrow worker login, configure only
test keys/prices and CLI forwarding, and restart the local app/worker. Preserve
existing profiles and Auth. Then verify the owner's normal login can reach
`/subscription`. No live Checkout or public deployment is included.
