# Поточний checkpoint

S00-03 завершено: фабрика FastAPI та `/health/live` працюють без БД/провайдерів.
Проєкт у корені, гілка `task/execution-v4`; origin — `ivan-zamurenko/handbalancers-studio`.
База S00-03: `f2e7d54` (S00-02 успішно запушено).
Push S00-03 виконується після комміту; фактичний SHA та результат — у звіті
власнику. Evidence зберігає статус на момент комміту: `pending_at_commit`.

## Перевірено

- Три нові тести спочатку впали через відсутню фабрику, після реалізації пройшли.
- `GET /health/live` → 200 `{"status":"ok"}` без мережевих звернень.
- Два застосунки не ділять змінювані settings, state, overrides або routes.
- Свіжий subprocess перевіряє відсутність I/O при import/startup/shutdown.
- `uv run --locked pytest -q`: 27 passed, 1 upstream warning.
- Ruff і граф 134 задач — без помилок; незалежне рев’ю — без блокерів.
- Реальний Uvicorn на loopback також повернув 200; процес після перевірки зупинено.

Starlette попереджає про майбутній перехід TestClient із httpx на httpx2;
зафіксовані версії сумісні, warning не приховано.
Команди, RED/GREEN і межі: `.workflow/evidence/S00-03.json`.
Версії та локальний PATH: `docs/toolchain-lock.md`.

## Наступний крок

S00-04: прочитати `roadmap/tasks/S00-04_settings.md`, написати тести
типізованих Settings, перевірки APP_ENV та нерозголошення секретів.
Наразі factory приймає копію явно переданого mapping, без читання environment.
БД, UI, авторизацію та платежі ще не реалізовано.

## Домовленості

Старий runtime не використовувати й не відновлювати. Усе створювати в корені.
Основна гілка — `task/execution-v4`; стару main видалено, історію збережено
під тегом `archive/pre-execution-v4`. Не створювати окремий проєкт/worktree.
