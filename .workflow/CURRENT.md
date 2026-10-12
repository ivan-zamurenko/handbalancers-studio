# Поточний checkpoint

S02-01 реалізовано: затверджені C1/A1/C3 tokens, базова типографіка,
системний шрифт, монохромні primary buttons і спільний Jinja base template.
S02-02 завершено локально: доступні Jinja form/error/button macros, native dialog,
async pending/error recovery і компонентні стилі. База: c99f1629dbb91e5487b1a2cb0c09b56f29b37829.
S02-03 завершено локально: auto/light/dark controller з device clock, workout hold,
manual override і early boot. База: e57a0352b5fc968d858608efbf4eb81b2eb0d994.
S02-04 завершено локально: спільні UK/EN dictionaries, locale fallback, language
partial та Intl number/date formatting. База: a46a61f67630f39be3b12066a3659d7cc42e3f9c.
S02-05 завершено й pushed: same-origin API client, CSRF token handling, classified
business/network errors і save-state mapping. Commit: f95993992a01637b56a4c2780d79f3af0461dc0f.
Гілка task/execution-v4; origin ivan-zamurenko/handbalancers-studio.
База комміту: 6190c78ebf80f6082ae735fb90dcdea31111d734 — S01-07 pushed,
fresh Supabase GitHub CI GREEN (run 37938338735).
S02-01 push/remote CI перевіряються після комміту.

## Перевірено

- S02-05 RED: `ERR_MODULE_NOT_FOUND` для відсутнього `server/static/js/api/client.js`.
- S02-05 GREEN: focused tests 5 passed; full JS suite 34 passed; syntax і editor
  diagnostics чисті.
- Same-origin credentials/CSRF, no blind POST retry, 409/401 draft preservation,
  typed API/network errors перевірено. Server-side CSRF issuance ще не підключений.
- Evidence: `.workflow/evidence/S02-05.json`.
- S02-04 RED: missing `studio.shared.i18n` та missing `format.js` imports.
- S02-04 GREEN: Python localization tests 4 passed; Intl tests 2 passed; full JS
  suite 29 passed; Ruff, scoped mypy та editor diagnostics чисті.
- UK/EN parity/non-empty keys, unknown-locale fallback, business payload isolation,
  escaped language links і selected locale перевірено.
- Evidence: `.workflow/evidence/S02-04.json`. Сторінки ще не інтегрували locale
  resolver; account preference sync та URL propagation залишаються майбутніми.
- S02-03 RED: controller import `ERR_MODULE_NOT_FOUND` до реалізації.
- S02-03 GREEN: focused theme tests 6 passed; full JS suite 27 passed з локальним
  Chromium cache; JavaScript syntax та editor diagnostics чисті.
- Auto межі 07:00–20:00, manual override (включно з OS change), storage failure,
  workout deferral, visibility/reload і незмінений form value перевірено.
- Boot script перед CSS; template передає CSP nonce. Сам nonce/CSP middleware ще не
  генерується застосунком; account preference та workout event producers — майбутні.
- Evidence: `.workflow/evidence/S02-03.json`.
- S02-02 RED: 3 expected `TemplateNotFound: shared/forms.html` failures.
- S02-02 GREEN: focused Playwright 4 passed; full e2e 7 passed; JS suite 21 passed.
- Verified label/error and summary links, modal Tab wrap/Escape/focus restore, repeat
  submit blocking/error recovery, and light/dark at 390/1440 without horizontal overflow.
- `uv lock --check` and JS syntax checks passed; evidence `.workflow/evidence/S02-02.json`.
- The card's `--project=chromium` option is unsupported; config has no named projects.
  Default browser is Chromium, and the actual suite passed without that flag.
- Product routes/static serving are not present yet; tests render real Jinja macros and
  inject actual assets. HTTP integration remains for a later card.

- RED: 7 очікуваних assertion failures до реалізації.
- GREEN: 7 нових tests; JS regression 21 passed.
- Chromium: light/dark × 390/1440, реальні computed colors, font, focus,
  control height і відсутність horizontal overflow; скриншоти переглянуто.
- Read-only review без блокерів; evidence .workflow/evidence/S02-01.json.
- Browser fixture перевіряє CSS; Jinja rendering/HTTP pages ще не підключені.
- Палітри/spacing/radii з design-tokens.json; типографіка з selected.css.
- User docs deletions/Copilot additions не змінено і не staged;
  локальний roadmap validate не GREEN через відсутні docs, контракти з HEAD.

## Наступний крок

S03-01 готовий: stateless HTTP gateway, 13 gateway / 40 unit tests GREEN.
Оригінальний RED попереднього WIP не зафіксовано; нові hardening RED/GREEN в evidence.
S03-02 готовий: 14 JWT security tests GREEN; обов’язковий suite у CI.
ES256/RS256, JWKS TTL300s/cooldown30s/deadline5s; ролі лише з БД.
Наступна картка S03-03 registration. Поточне доручення — працювати до запущеного лендінгу S05-03.
Реальні Supabase roundtrips ще не перевірені. Raw gateway dict не trusted identity.
S02-01 не реалізує сторінки C1/A1/C3 або controller тем; base має dark fallback
референсу, майбутній controller задаватиме фактичну тему/auto.
HTTP static/templates integration додати при першій сторінці, без fake/demo routes.

## Локальний стенд

Docker у Colima studio-s01; окремі dev/test Supabase profiles.
Test PostgreSQL 127.0.0.1:55322, HTTP 55321, revision 0004.
Managed Auth під керуванням Supabase; Alembic лише studio/studio_private.

    export PATH="$PWD/.local-tools/node/bin:$PWD/.local-tools/uv-env/bin:$PWD/.local-tools/supabase-cli/node_modules/.bin:/opt/homebrew/bin:$PATH"
    export UV_CACHE_DIR="$PWD/.local-tools/uv-cache"
    export PLAYWRIGHT_BROWSERS_PATH="$PWD/.local-tools/playwright-browsers"
    export DOCKER_HOST="unix://$HOME/.colima/studio-s01/docker.sock"
    unset DOCKER_CONTEXT
    node --test tests/js/*.test.js
    uv run --locked python -m tools.check_migrations

--fresh лише для нового test stack, не очищає наявну БД.
Ключі не друкувати; .local-tools/supabase містить приватні локальні файли.
S01-06 storage не є повною автентифікацією; provider/key-loader/HTTP auth попереду.
External exchange лише після commit consume_attempt. Google/Apple/email не перевірені.

## Домовленості

Новий runtime з нуля, все в корені; старий runtime не відновлювати.
Основна гілка task/execution-v4; історія під archive/pre-execution-v4.
Не створювати окремий проект/worktree. Не відновлювати user-deleted docs.
