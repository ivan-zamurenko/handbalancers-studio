# S03-06: bounded session refresh

Decision: 2026-11-07. Implements the resumed S03-06 card. No new public endpoint.

## Lifetime and trust

A new verified login creates an opaque local session with a fixed seven-day maximum
(engineering default, not an owner-specified product requirement). Access expiry is
separate. Refresh never extends the local deadline and never changes the product
user, upstream session UUID, cookie hash or product role. Existing sessions retain
their original deadline; already expired sessions require a new login.

The existing JWT signature/issuer/audience/expiry validation remains mandatory.
After refresh, signed user/session claims must match the current active product
profile and the stored upstream session. The profile/role and local revocation are
rechecked after network I/O. Successful identity does not imply a paid entitlement.
JWT verification alone does not guarantee immediate upstream revocation; ordinary
requests use the existing JWT validator (JWKS TTL 300 seconds), while refresh checks
with Supabase. This card does not add sensitive product operations.

## Coordination without a transaction across network I/O

The existing `row_version` is a fencing counter: odd means idle, even means a
refresh claim. `last_seen_at` records the latest successful refresh claim time,
using PostgreSQL time; it is not a general last-page-view timestamp. A claim updates
both columns in a short transaction, only for a live local session whose access
cache has expired. A 30-second expired claim can be replaced, advancing the fencing
counter. No process-local mutex or connection-affine advisory lock is required.

Waiters reread committed state every 50 ms for at most six seconds of contention.
Each winner makes one exchange and verifies the JWT within a five-second async
deadline. Runtime DB statements have the existing five-second statement timeout and
two-second lock timeout. Network calls hold no DB transaction or checked-out DB
connection. The wait deadline bounds polling, not a stalled OS/process or the full
request including connection acquisition.

Completion uses a version/lease/lifetime/revocation predicate and one atomic UPDATE
for encrypted access+refresh tokens, access expiry and the next idle version.
AEAD associated data uses the new access expiry. A stale worker cannot overwrite
or revoke a successor's state. Logout during exchange wins. Rollback leaves the
previous encrypted pair and expiry together. Temporary failure/cancellation releases
only the caller's claim. If cleanup cannot reach the DB, lease expiry permits recovery.

A five-second local timeout cannot undo an exchange already processed by Supabase.
A process crash after exchange and before DB commit can require another exchange.
We do not claim exactly-once external execution or rely on a particular provider
reuse window. Recovery may ultimately require a new login if Supabase rejects the
retained token. No automatic upstream retry loop is added.

## Failure behavior

Definitive rejected/invalid upstream credentials revoke the local session with the
same fencing predicate and return 401. A changed signed identity/session also does
so. Timeout, rate limiting, unavailable provider/DB, a busy lease or malformed
response returns 503 with no-store and no authenticated success. JWT verification
failure during rotation is retryable because the current validator uses the same
exception for invalid signatures and unavailable JWKS: the request fails closed,
but an ambiguous failure does not permanently log the user out. Tokens and provider
response bodies never appear in response payloads or application logs.

## Scope and rollout

The original card said no schema change. No tables or columns are added; narrow
Alembic 0007 grants UPDATE on four existing columns only to studio_auth_runtime:
`encrypted_tokens`, `access_expires_at`, `row_version`, `last_seen_at`. Existing
revocation permission and RLS remain. No UPDATE of identity, cookie or local lifetime
is granted. Migration downgrade is explicit forward repair, matching earlier cards.

The migration is tested only on the guarded local test stack. Cloud remains at the
verified baseline 0006. `tools.migrate_cloud` stays pinned to 0006 even when the local
migration graph has a later head; this command does not authorize or apply 0007.
Apply/rehearse 0007 separately before deploying this runtime to the cloud. No cloud
DB change or deployment is part of this implementation.

## Evidence

See `.workflow/evidence/S03-06.json`. Tests use real PostgreSQL grants, RLS and crypto,
independent service instances, overlap, stale-lease fencing, rollback, logout race,
identity mismatch, bounded timeout and cancellation. The separate local Supabase
roundtrip uses real Auth/JWT with a deliberately shortened local access-cache expiry;
it does not claim a cloud refresh smoke test.

Sources checked: [Supabase sessions](https://supabase.com/docs/guides/auth/sessions),
[Supabase changelog](https://supabase.com/changelog), and the relevant
[TLS deprecation](https://supabase.com/changelog/cbc-tls-ciphers-deprecated).
The TLS notice requires no API or SDK change here; default modern TLS is retained.
