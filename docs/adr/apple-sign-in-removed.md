# Apple sign-in removed

Decision: 2026-11-16, owner. Confirms the 2026-11-07 exclusion.

## Decision

Handbalancer’s Studio has no "Sign in with Apple". Sign-in methods are
Google OAuth and email/password, both through Supabase Auth.

## Why

- Apple requires a paid Apple Developer Program membership. The owner does
  not want to pay for it.
- Google plus email/password already cover the target audience. Keeping a
  disabled provider in code added untested surface (config flag, allowlist,
  tests) with no product value.

## What changed (commit 9579855)

- Provider allowlist is google-only in `OAuthService.start` and
  `TokenStore.create_attempt`; config cannot re-enable Apple.
- `oauth_apple_enabled` / `OAUTH_APPLE_ENABLED` removed from settings and
  `.env.example`. An old env line is ignored (only declared names are read).
- Roadmap: S04-03 `apple_adapter` is `skipped`; S04-04 depends on S04-02.
  S17-01 no longer checks Apple.

## Not changed

The DB CHECK `ck_attempts_provider` (migration 0004) still allows `'apple'`.
The app cannot write it; tightening it needs a new migration and is not
required.

## For agents

Do not add Apple back, re-introduce the flag, or plan Apple tasks unless the
owner explicitly asks in a new instruction. Old docs/cards that mention Apple
are historical.
