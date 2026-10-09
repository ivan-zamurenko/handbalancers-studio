# Поточний checkpoint

S02-01 реалізовано: затверджені C1/A1/C3 tokens, базова типографіка,
системний шрифт, монохромні primary buttons і спільний Jinja base template.
S02-02 завершено локально: доступні Jinja form/error/button macros, native dialog,
async pending/error recovery і компонентні стилі. База: c99f1629dbb91e5487b1a2cb0c09b56f29b37829.
Гілка task/execution-v4; origin ivan-zamurenko/handbalancers-studio.
База комміту: 6190c78ebf80f6082ae735fb90dcdea31111d734 — S01-07 pushed,
fresh Supabase GitHub CI GREEN (run 37938338735).
S02-01 push/remote CI перевіряються після комміту.

## Перевірено

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

S02-03: theme clock. Прочитати картку через `python tools/roadmap.py next`.
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
