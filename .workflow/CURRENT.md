# Оновлення2026-10-19

S05-03b: підписана схема поступу та SVG спорядження,4browserGREEN,reviewclean.
Далі явне доручення власника — форма/login (UI,повна authнепідключена).
Попередній лендінгbd051b6pushed/CIgreen(run38286710967).

# Поточний checkpoint — 2026-10-12

Локальний лендінг запущено: http://127.0.0.1:8000 і /plans.
S05-03a — незалежний публічний зріз для перегляду за дорученням власника
працювати до запущеного лендінгу. Повний S05-03 та S03-04..S05-02 залишаються todo.
Тести → код → перевірки → окремі комміти збережено; порядок public preview
виділено явно, не позначаючи пропущені auth/onboarding залежності завершеними.

## Зроблено цього проходу

- S03-01: gateway, commit80d49b0 (push), 13gatewaytests. Початковий WIP уже
  містив код; оригінальний RED невідомий, нові hardening RED/GREEN зафіксовано.
- S03-02: JWT ES256/RS256, claims/JWKS bounded refresh, commit02b0f58 (push/CIgreen).
  TTL300s/cooldown30s/fetch deadline5s. JWT не заміняє role/revoke/freshness checks.
  Security suite додано до CI. Виправлено попередній format дефект i18n.py.
- S03-03: register input→pending202 без cookie/DB profile, commit5c8d3e8 (push/CIgreen,
  run38285362953). Gateway runtime config ще не підключено: default503.
- S05-03a: approved public copy, index/plans, static mount, native radios,
  theme/locale selectors, remembered plan, honest unavailable dialog, no fake APIs.
  Push/CI S05-03a перевіряються після комміту.

## Перевірено

72 Python unit/contracts/security tests; 34JS; full e2e16 до додаткового тесту H1;
фінальний public e2e10GREEN. Ruff і mypyGREEN. 390/1440 ×light/dark переглянуто.
Read-only review: no blockers; H1 на standaloneplans виправлено з regression.
Graph validatorGREEN. Working-tree roadmap file validation неGREEN через
user-deleted docs; їх не відновлювали, прочитані контракти з HEAD.
Реальний devserverHTTP200, без горизонтального overflow та JS помилок.

## Запуск

    export PATH="$PWD/.local-tools/uv-env/bin:$PATH"
    export UV_CACHE_DIR="$PWD/.local-tools/uv-cache"
    uv run --locked python tools/serve_preview.py

Залишено власний процес на127.0.0.1:8000; для нового запуску вільний порт8000.
Інструкція .workflow/LOCAL_PREVIEW.md. Публічний preview не читає provider secrets.
Працюють секції, мови, теми, тарифи та вибір. Вхід/оплата/AI ще недоступні,
це видно на сторінці й у діалозі. Немає deployment або реальних платежів.

## Наступний крок

Основна послідовність: S03-04 verify email, далі auth/profile/onboarding;
потім інтегрувати public preview з повним S05-03. Не вважати frontend choice
server entitlement, raw gateway dict — verified identity, JWT — current product role.

## Стенд та домовленості

Гілка task/execution-v4, origin ivan-zamurenko/handbalancers-studio.
Новий runtime з нуля у корені; старий не використовувати/відновлювати.
Архів історії archive/pre-execution-v4. User docs deletions/Copilot/.vscode не чіпати.

Docker Colima studio-s01; test PostgreSQL127.0.0.1:55322, HTTP55321, migration0004.
Managed Auth належить Supabase. 18auth-storage DBtests пройшли цього проходу.

    export PATH="$PWD/.local-tools/node/bin:$PWD/.local-tools/uv-env/bin:$PWD/.local-tools/supabase-cli/node_modules/.bin:/opt/homebrew/bin:$PATH"
    export PLAYWRIGHT_BROWSERS_PATH="$PWD/.local-tools/playwright-browsers"
    export DOCKER_HOST="unix://$HOME/.colima/studio-s01/docker.sock"
    unset DOCKER_CONTEXT
    uv run --locked python -m tools.check_migrations

--fresh лише для нового teststack, без reset. Ключі не друкувати.
Google/Apple/email live roundtrips не виконано. External exchange після commit consume_attempt.
