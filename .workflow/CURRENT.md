# Поточний checkpoint

S00-06 завершено: єдиний HTTP error envelope та server-generated request_id.
Проєкт у корені, гілка `task/execution-v4`; origin — `ivan-zamurenko/handbalancers-studio`.
База S00-06: `e8c7b83` (S00-05 успішно запушено).
Push після комміту; SHA та результат у звіті власнику. Evidence фіксує момент
перед push: `pending_at_commit`.

## Перевірено

- 422/500/стандартні HTTP-помилки мають error:{code,message_key,field_errors,request_id}.
- Клієнт не отримує SQL, exception detail, traceback або значення полів.
- X-Request-ID однаковий у header, error body та studio.access; caller ID ігнорується.
- Access-log лише ID/статус; Uvicorn raw URL log відфільтровано.
- Реальний loopback Uvicorn підтвердив відсутність синтетичних секретів у stdout/stderr.
- 59 Python-тестів, 3 subtests, 14 Node-тестів пройшли. Один відомий Starlette warning.
- Ruff/граф задач валідні. Незалежне рев'ю без блокерів.

field_errors наразі вказують лише розділ body/query/path/header/cookie, не
динамічні назви полів. Після відправлення заголовків новий 500 envelope неможливий;
виняток замінюється безпечним повідомленням без первісних деталей.
Команди й RED/GREEN: `.workflow/evidence/S00-06.json`.

## Наступний крок

S00-07: прочитати `roadmap/tasks/S00-07_ci_baseline.md`, почати з тестів CI baseline.
Повний pytest потребує Chromium/loopback; PLAYWRIGHT_BROWSERS_PATH та PATH —
у README і docs/toolchain-lock.md. Backend-only: `uv run --locked pytest server/tests -q`.
UI, БД, auth та платежі ще не реалізовано. Supabase заплановано для PostgreSQL/Auth.

## Домовленості

Старий runtime не використовувати й не відновлювати. Усе створювати в корені.
Основна гілка — `task/execution-v4`; стару main видалено, історію збережено
під тегом `archive/pre-execution-v4`. Не створювати окремий проєкт/worktree.
