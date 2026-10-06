# Начало в чистой папке и локальные команды

## Что уже лежит в kit
Документы, task graph, workflow selector, тесты selector, агентская конфигурация и исторические reference-макеты. Ни FastAPI runtime, ни product SQL миграций пока нет. `references/design/preview/index.html` — макет, не сайт новой реализации. Содержимое `.codex` применять только после ручного обзора/trust; это не глобальный auto-install.

## Первый сеанс S00
Распаковать kit в новую отдельную папку, не поверх старого проекта. Сверить `git status`, существование `.git` и пользовательских файлов. Если там только kit, допустимо сделать его корнем нового репозитория. Не связывать старый origin автоматически. Запустить доступные уже сейчас команды:
```sh
python tools/roadmap.py validate
python tools/roadmap.py next
python tools/roadmap.py show S00-01
python -m unittest discover -s tools/tests -v
```
Затем выполнить S00-01; S00-02 создаёт pyproject/package manifests и lockfiles. Первую задачу нельзя объявлять сделанной только потому, что zip распакован: зафиксировать безопасное рабочее окружение, проверку исключений Git и baseline.

## Фиксация версий
Baseline: Python3.13, Node24 (только tooling), SQLAlchemy2, psycopg3 sync. Patch versions и SDK выбираются один раз по реальной совместимости в S00-02, записываются lockfiles; дальше только locked installs. FastAPI/Jinja/Uvicorn/Pydantic-settings/HTTPX и Supabase client по необходимости. Не копировать пакеты исторического React.

Supabase CLI локально управляет PostgreSQL/Auth. Версию PostgreSQL выбирать совместимую с фактическим local/staging Supabase, записать в toolchain-lock. Не создавать одновременно отдельный неподключённый postgres compose как «настоящую» DB для всех tests. Для unit DB не нужна; интеграции используют guarded local disposable project.

## Команды после их реализации
```sh
uv sync --locked
npm ci
uv run uvicorn studio.main:create_app --factory --host 127.0.0.1 --port 8000
uv run alembic -c alembic.ini upgrade head
uv run pytest server/tests/unit -q
uv run pytest server/tests/contracts -q
node --test tests/js/*.test.js
npx playwright test --project=chromium
```
До появления соответствующих tasks команда может закономерно не существовать. `alembic.ini` добавить в S01 migration-baseline и зарегистрировать в project map. Integration/security tests должны проверить loopback/project/port/test marker до любой записи. SQLite не substitute проверки PostgreSQL RLS/locks.

## CI и окружения
local-dev и local-test раздельны: ports, Supabase project_id, volumes, environment, cookie domains. Worktree writers также не делят один test database. staging — отдельный явно разрешённый target для внешних проверок. Production никогда не берётся из `.env` случайным fallback.

Secrets: `APP_ENV`, `PUBLIC_ORIGIN`, `DATABASE_URL`, `AUTH_DATABASE_URL`, `WORKER_DATABASE_URL`, `SUPABASE_URL`, publishable public key, encrypted-token key IDs, Stripe/webhook keys — типизированы Settings. Пример env не содержит значений. Service-role если вообще нужен узкому owner/auth-tool остаётся серверным и не является обычной product DB ролью.

Lock changes — отдельный review. Первое получение зависимостей/браузеров требует разрешённой сети; кэшировать installs в CI. Не включать danger-full-access ради установки пакета. Не ограничивать локальное чтение/редактирование/test suite лишним ручным подтверждением каждого файла.

## Проверено здесь, не на твоём компьютере
В подготовке kit проверяются workflow utility, JSON/TOML и HTML package. В данной среде Codex CLI и Docker не установлены: реальная загрузка конфигурации Codex, Supabase containers, OAuth/Stripe/product tests не выполнялись. Следующий агент обязан проверить версии и возможности своей среды, не повторять исторические «passed» как новые результаты.
