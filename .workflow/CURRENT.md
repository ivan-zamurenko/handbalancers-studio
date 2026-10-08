# Поточний checkpoint

S00-07 завершено локально: CI baseline на push/pull_request.
Проєкт у корені, гілка task/execution-v4; origin — ivan-zamurenko/handbalancers-studio.
База: dde6a1c (S00-06 запушено). Push і фактичний GitHub CI перевіряються після
комміту; результат і SHA — у звіті власнику. Evidence зберігає pending_at_commit.

## Перевірено

- python3 tools/checks.py: Ruff/format/mypy, unit/HTTP/tooling/browser/Node, roadmap.
- 64 Python-тести, 8 subtests, 14 Node-тестів; справжній Chromium через tooling suite.
- Відсутній suite або помилка команди зупиняють runner.
- Locked installs; Actions pinned upstream SHA; contents:read; без production secrets.
- Незалежне рев'ю без блокерів. Відомий Starlette warning не приховано.
- RED/GREEN та межі: .workflow/evidence/S00-07.json.

## Наступний крок

S01-01: roadmap/tasks/S01-01_local_supabase.md — ізольований локальний Supabase
для dev/test. Почати з тестів захисту стенда. Docker/реальний DB стенд ще не перевірено.
Повний CI потребує Chromium/loopback; PATH та PLAYWRIGHT_BROWSERS_PATH — у README
і docs/toolchain-lock.md. UI, БД, auth та платежі ще не реалізовано.

## Домовленості

Старий runtime не використовувати й не відновлювати. Усе створювати в корені.
Основна гілка task/execution-v4; стару main видалено, історію збережено під
archive/pre-execution-v4. Не створювати окремий проєкт/worktree.
