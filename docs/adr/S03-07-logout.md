# S03-07: local logout and account cache cleanup

2026-11-07. Logout revokes the opaque local session in a committed transaction
before any upstream call. Expired or unreadable encrypted tokens cannot suppress
revocation. Repeating the request with the same cookie and valid CSRF returns 204
without exposing an identity or requiring another upstream call. A request without
cookie/CSRF, with another cookie's CSRF, or with a foreign Origin remains 403.

Supabase sign-out is explicitly `scope=local`, preserving other device sessions.
A five-second total async deadline bounds the best-effort request, outside the DB
transaction. The service returns True/False/None for upstream confirmed/unconfirmed/
not attempted; HTTP 204 confirms local logout only. The cookie is expired with its
original Path/HttpOnly/Secure/SameSite attributes. Local revocation is immediate;
the HTTP response waits at most the upstream deadline in addition to DB work.
Upstream failure never undoes revocation. No background queue or new endpoint.

Browser credentials, CSRF and active profile ID remain in memory. Private browser
storage uses `studio:account:<profile-id>:<key>`; the cleanup helper removes matching
localStorage and sessionStorage keys. No private draft/cache writers existed before
this card. Future writers must use this namespace; this is not an IndexedDB or
CacheStorage implementation (neither is used by current code). Guest theme, public
preferences and other account namespaces are preserved. Cleanup is performed on
204, a confirmed guest/401 snapshot, or an observed account change. A network error
is ambiguous: the controller reconciles with the server instead of declaring
logout or discarding drafts. Pending snapshots cannot restore pre-logout state.
Storage API denial must not prevent server logout/navigation.

Cleanup covers this document's memory and tab sessionStorage plus shared localStorage.
Cross-tab messaging and future offline storage are not added by this card. Pageshow
revalidates server state. Server authorization never depends on browser cache state.

Security tests exercise pre-DB Origin/CSRF. Real-DB cases are in the integration
suite, because the baseline security suite is intentionally runnable without a DB.
A real local Supabase test proves old refresh rejection and survival of a second
upstream session. Browser tests cover 390/1440 and both themes, response loss,
failed logout, blocked storage and an overlapping session snapshot. See evidence.

No schema changes or cloud/deployment operations. Cloud 0007 from S03-06 remains
pending; verified local logout is not a claim of hosted provider readiness.
Reference: [Supabase sign-out scopes](https://supabase.com/docs/guides/auth/signout).
