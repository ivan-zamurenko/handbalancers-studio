# Поточний checkpoint

S01-01: локальний runner та захист реалізовано; реальна БД має статус env_blocked.
Проєкт у корені, гілка task/execution-v4; origin — ivan-zamurenko/handbalancers-studio.
База: 05ef7f3 (S00-07). SHA поточного комміту й push — у звіті після комміту.
Картку не позначено done: tooling GREEN не доводить реальну DB-ізоляцію.

## Перевірено

- S01-01: 16 unittest-тестів; pytest також GREEN.
- Affected suite: 80 тестів, 24 subtests; наявний Starlette warning не приховано.
- Ruff та mypy для нового коду GREEN; mypy потребує --explicit-package-bases.
- dev/test мають різні project_id, порти, workdirs і приватні credential-файли.
- Guard перевіряє URL, Docker socket, project label, container/volume name та порт.
- Прямий fixture-guard відхиляє PG* overrides; runner очищує їх перед запуском.
- Test runner не запускає/не скидає БД. Product DDL ще немає.
- Read-only review: обхід через PGHOSTADDR відтворено RED і виправлено; повторне рев'ю без блокерів.
- Supabase CLI 2.120.0 встановлено в .local-tools/supabase-cli, ES256 генерація працює.
- Реальний start test зупинився на Docker; parse-error конфігурації не виявлено.
- RED/GREEN, незакриті live-перевірки: .workflow/evidence/S01-01.json.

## Наступний крок

Встановити й запустити Docker Desktop або сумісний локальний Docker daemon.
/usr/local/bin/docker зараз є непрацездатним посиланням. Remote Docker заборонено.
Далі з кореня, з PATH із docs/toolchain-lock.md та CLI у PATH:

```sh
export PATH="$PWD/.local-tools/supabase-cli/node_modules/.bin:$PATH"
uv run --locked python tools/local_stack.py start dev
uv run --locked python tools/local_stack.py start test
uv run --locked python tools/local_stack.py test -- .venv/bin/python -c 'from server.tests.support.database_guard import require_test_database; require_test_database()'
```

Перевірити фактичні доступи, marker/volumes і незмінність dev-даних після повторних
тестових запусків. Ефект SUPABASE_DB_PASSWORD на живій БД ще не доведено;
за потреби виправити підключення секретів, не послаблювати ізоляцію.
Ключі не друкувати; .local-tools/supabase містить приватні локальні файли.
Supabase може публікувати Docker-порти на всіх інтерфейсах: guard URL не є firewall.
S01-02 та інші залежні DB-картки не починати до реального GREEN S01-01.

## Домовленості

Старий runtime не використовувати й не відновлювати. Усе створювати в корені.
Основна гілка task/execution-v4; стару main видалено, історію збережено під
archive/pre-execution-v4. Не створювати окремий проєкт/worktree.
