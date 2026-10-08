# Поточний checkpoint

S00-05 завершено: Node test runner і Playwright працюють із локальним test app.
Проєкт у корені, гілка `task/execution-v4`; origin — `ivan-zamurenko/handbalancers-studio`.
База S00-05: `0e94641` (S00-04 успішно запушено).
Push цієї картки — після комміту; SHA та результат у звіті власнику.
Evidence фіксує момент перед push: `pending_at_commit`.

## Перевірено

- 14 Node-тестів пройшли; дозволено лише http://127.0.0.1:8765.
- 4 Python harness-тести пройшли, включно зі справжніми Chromium-сценаріями.
- Браузер бачить реальну liveness-відповідь 200 {"status":"ok"}.
- Cookies/localStorage/sessionStorage між тестами ізольовані.
- Runner відхиляє зовнішні адреси, dev-порт 8000 та зайнятий test-порт.
- Повний pytest: 54 passed, 3 subtests passed, 1 відомий Starlette warning.
- Ruff і граф задач валідні, read-only рев'ю без блокерів.

Команди: `npm run test:js`, `npm run test:e2e`.
Для браузера потрібен `PLAYWRIGHT_BROWSERS_PATH="$PWD/.local-tools/playwright-browsers"`;
встановлення Chromium: `npx playwright install chromium`. PATH та версії —
у docs/toolchain-lock.md. Повний pytest тепер потребує браузера і loopback.
Вузькі backend-тести: `uv run --locked pytest server/tests -q`.

## Наступний крок

S00-06: прочитати `roadmap/tasks/S00-06_error_contract.md`, почати з тестів
єдиного контракту HTTP-помилок. UI, БД, auth, платежі ще не реалізовано.
Supabase залишається запланованим PostgreSQL/Auth; браузер працюватиме через FastAPI.
Поточний browser harness не призначений для staging/production.

## Домовленості

Старий runtime не використовувати й не відновлювати. Усе створювати в корені.
Основна гілка — `task/execution-v4`; стару main видалено, історію збережено
під тегом `archive/pre-execution-v4`. Не створювати окремий проєкт/worktree.
