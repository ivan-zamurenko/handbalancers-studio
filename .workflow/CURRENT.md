# Поточний checkpoint

S00-04 завершено: типізовані Settings і безпечна валідація запуску.
Проєкт у корені, гілка `task/execution-v4`; origin — `ivan-zamurenko/handbalancers-studio`.
База S00-04: `4d5a731` (S00-03 успішно запушено).
Push S00-04 виконується після комміту; фактичний SHA та результат — у звіті
власнику. Evidence фіксує момент перед push: `pending_at_commit`.

## Перевірено

- APP_ENV обов'язковий: local-dev, local-test, test, staging або production.
- Production/staging не стартують без HTTPS origin і непорожнього ключа.
- SecretStr, незмінні Settings, безпечні ValidationError/JSON/errors/traceback.
- Некоректний JSON також не показує початкових значень.
- Factory повторно перевіряє передані Settings; явні test settings не читають env.
- Environment loader читає тільки оголошені імена, .env автоматично не читається.
- 50 тестів пройшли, Ruff і граф задач валідні. Одне відоме попередження Starlette.
- Реальний процес з небезпечною production-конфігурацією відхилено без витоку секретів.
- Незалежне рев'ю — без блокувальних зауважень.

Команди й RED/GREEN: `.workflow/evidence/S00-04.json`.
Локальний запуск із явним APP_ENV описано в README.

## Наступний крок

S00-05: прочитати `roadmap/tasks/S00-05_js_harness.md`, написати тести JS harness.
UI, БД, auth, платежі ще не реалізовано. Supabase заплановано для PostgreSQL
і Auth за Execution V4; браузер працює через FastAPI. Підключення ще немає.
Формат ключа й алгоритм шифрування визначатимуться в задачі їх використання;
поточна перевірка наявності ключа не є production readiness.

## Домовленості

Старий runtime не використовувати й не відновлювати. Усе створювати в корені.
Основна гілка — `task/execution-v4`; стару main видалено, історію збережено
під тегом `archive/pre-execution-v4`. Не створювати окремий проєкт/worktree.
