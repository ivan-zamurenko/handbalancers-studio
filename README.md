# Handbalancer’s Studio

Застосунок для практики балансу на руках. Стек: FastAPI, SQLAlchemy 2,
PostgreSQL / Supabase Auth, Jinja, CSS і vanilla JavaScript.

Працюють публічні сторінки, тарифи, UK/EN, світла/темна тема та форми авторизації:
реєстрація, підтвердження email, вхід із паролем, Google, відновлення і вихід.
Доступність email/Google залежить від налаштувань сервера. Apple вимкнено.
Оплата, кабінет і тренувальні сценарії ще розробляються.

Поточний стан і невиконані перевірки — у [checkpoint](.workflow/CURRENT.md).
Загальний план — [ROADMAP](roadmap/ROADMAP.md), наступна картка:

```sh
.venv/bin/python tools/roadmap.py next
```

## Структура

| Шлях | Призначення |
|---|---|
| `server/studio/` | HTTP-застосунок; модулі auth, accounts, public та shared |
| `server/templates/auth/` | Усі сторінки й частини форм авторизації |
| `server/templates/public/` | Лендінг, тарифи та публічний layout |
| `server/templates/shared/` | Спільні елементи інтерфейсу |
| `server/static/` | Лише ресурси продукту; `css/auth.css` — спільні стилі Auth |
| `server/alembic/` | Версійні міграції БД |
| `server/tests/` | Python unit, HTTP, security та integration тести |
| `tests/` | JavaScript, браузерні тести й їхні fixtures |
| `tools/` | Локальні інструменти розробки, міграцій і перевірок |
| `tools/previews/handstand/` | Збережені варіанти анімації; не публікуються застосунком |
| `.workflow/` | Поточний стан, evidence та архів checkpoint у `history/` |
| `roadmap/`, `docs/` | Картки, специфікації, рішення й інструкції |
| `references/`, `checks/`, `prompts/`, `agent-config/` | Матеріали вихідного комплекту, не runtime |

`00_READ_FIRST.md`, `AGENT_START_RU.txt`, `START_HERE.html`, `MANIFEST.json`
та `SHA256SUMS.txt` збережені як історичні матеріали комплекту Execution V4.
Manifest і контрольні суми описують вихідний ZIP, а не поточний код.
Робота ведеться в корені, у гілці `task/execution-v4`.

## Локальний запуск

Версії зафіксовані у `.python-version`, `.node-version`, `pyproject.toml` і
`package.json`; Python та JS залежності — в `uv.lock` і `package-lock.json`.

```sh
uv sync --locked
npm ci
export PLAYWRIGHT_BROWSERS_PATH="$PWD/.local-tools/playwright-browsers"
npx playwright install chromium
```

Перегляд дизайну без ключів, БД й зовнішньої авторизації:

```sh
uv run --locked python tools/serve_preview.py
```

Відкрити http://127.0.0.1:8000. Галерея руху в цьому режимі:
http://127.0.0.1:8000/_previews/handstand/index.html.
Цей сервер явно ігнорує налаштування провайдерів із середовища.

Для роботи з уже налаштованою авторизацією:

```sh
uv run --locked --env-file .env.local uvicorn studio.main:create_app --factory --host 127.0.0.1 --port 8000
```

`.env.local` приватний і виключений із Git. Не перегенеровуйте ключ шифрування
під час перезапуску. Налаштування описані в `.env.example` та
[інструкції Auth](docs/oauth-project-setup.md). Фабрика застосунку сама `.env`
не читає; команда вище підключає його явно. Вибирайте один сервер для порту 8000.
Зупинка — Ctrl+C. `GET /health/live` перевіряє лише роботу процесу.

## Перевірки

```sh
uv run --locked python tools/checks.py
npm run test:e2e
```

`checks.py` запускає lint/type checks, Python unit/contract/security/tooling,
JS і roadmap validator. `test:e2e` перевіряє весь браузерний набір.
Він сам запускає ізольований сервер на `127.0.0.1:8765`; порт має бути вільним.
Інші origin, зокрема dev-порт 8000, відхиляються до запуску тестів.

Вузькі перевірки без БД:

```sh
uv run --locked pytest server/tests/unit server/tests/contracts server/tests/security/auth -q
npm run test:js
```

DB/RLS/integration тести потребують окремого локального Supabase:

```sh
uv run --locked python tools/local_stack.py prepare test
uv run --locked python tools/local_stack.py start test
uv run --locked python tools/local_stack.py provision-migrations test
uv run --locked python -m tools.check_migrations
```

Для першої перевірки порожніх продуктових схем можна додати `--fresh`;
на вже мігрованій тестовій БД цей прапорець навмисно відхиляє запуск.

Ці команди призначені для ізольованого test stack, не для хмарної БД.
CI використовує зафіксовані залежності й окремий DB job; автоматичного deploy немає.
Зелені локальні тести не підтверджують hosted OAuth, доставку листів або оплату.

## Роль тренера (coach)

Публічної реєстрації тренера немає. Роль видає власник операторською командою за
Supabase auth UUID уже підтвердженого користувача (не за email); кожна зміна
пишеться в `studio_private.audit_events`:

```sh
STUDIO_MIGRATION_DATABASE_URL=… uv run --locked python -m studio.accounts.cli grant-coach <auth_user_id> --actor <ім'я>
STUDIO_MIGRATION_DATABASE_URL=… uv run --locked python -m studio.accounts.cli revoke-coach <auth_user_id> --actor <ім'я>
```

Потрібна міграція `0008_audit`. У хмарній БД вона ще не застосована.

## Робочі правила

[AGENTS.md](AGENTS.md) описує межі змін, перевірки й handoff.
Секрети, сесії, дампи та приватні відео не додаються в Git. `.gitignore`
не перевіряє вміст довільного файлу: перед комітом потрібен перегляд staged diff.
