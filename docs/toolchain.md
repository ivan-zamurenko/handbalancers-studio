# Локальні інструменти та команди

## Робоче середовище

Працюємо в наявному корені цього репозиторію, гілка `task/execution-v4`.
FastAPI runtime, міграції, локальний Supabase та public/auth UI вже є.
Не створювати вкладений execution-v4 або новий робочий проєкт.
Історичні матеріали kit у references не визначають поточну готовність.

```sh
.venv/bin/python tools/roadmap.py validate
.venv/bin/python tools/roadmap.py next
```

Поточний стан — `.workflow/CURRENT.md`; структура й запуск — README.md.

## Версії та встановлення

Python/Node/uv та залежності зафіксовано в `.python-version`, `.node-version`,
`pyproject.toml`, `package.json`, `uv.lock` і `package-lock.json`.
`docs/toolchain-lock.md` зберігає докази початкового вибору й подальші доповнення.
Не оновлювати залежності під час не пов’язаної з цим задачі.

```sh
uv sync --locked
npm ci
export PLAYWRIGHT_BROWSERS_PATH="$PWD/.local-tools/playwright-browsers"
npx playwright install chromium
uv run --locked python tools/serve_preview.py
```

Це credential-free preview на `127.0.0.1:8000`. Налаштований Auth runtime:

```sh
uv run --locked --env-file .env.local uvicorn studio.main:create_app --factory --host 127.0.0.1 --port 8000
```

Файл середовища підключається явно; секрети не зберігати в Git чи логах.
Наявний ключ шифрування не перегенеровувати для звичайного перезапуску.

## Перевірки

```sh
uv run --locked python tools/checks.py
uv run --locked pytest server/tests/unit server/tests/contracts server/tests/security/auth -q
npm run test:js
npx playwright test
```

Playwright використовує один неназваний Chromium project, власний порт 8765
і явні local-test налаштування. `--project=chromium` у старих картках не відповідає
поточному config; потрібен запуск без цього прапорця.

DB/RLS/concurrency перевірки виконуються лише на ізольованому test stack:

```sh
uv run --locked python tools/local_stack.py prepare test
uv run --locked python tools/local_stack.py start test
uv run --locked python tools/local_stack.py provision-migrations test
uv run --locked python -m tools.check_migrations
```

Для першої перевірки порожніх продуктових схем можна додати `--fresh`;
на вже мігрованій тестовій БД цей прапорець навмисно відхиляє запуск.

`local-dev` і `local-test` мають окремі порти, project IDs та volumes.
Перед записами integration harness перевіряє loopback/project/port/test marker.
SQLite не замінює PostgreSQL RLS/locks. Не запускати наведені test-команди
проти хмарної БД; cloud tooling має окрему авторизацію й перевірки.

## Межі доказів

Local unit/browser/integration GREEN не підтверджує hosted OAuth, email,
Stripe або production readiness. Невиконані зовнішні перевірки зберігаються
в state/evidence. Наявність CLI чи ключа не є дозволом на deploy або витрати.
