# Handbalancer’s Studio

Сайт і онбординг на **HTML/CSS/vanilla JavaScript + FastAPI + PostgreSQL**. Українська за замовчуванням, English; темний дизайн Sculpture.

Основний шлях: онбординг → тариф → реєстрація або вхід → оплата чи тріал → кабінет.

## Новий застосунок

- `server/studio/` — FastAPI, валідація, сесії, SQLAlchemy та інтеграції.
- `server/templates/`, `server/static/` — HTML, CSS, JS, локальні зображення.
- `server/alembic/` — міграції PostgreSQL.
- `server/tests/` — серверні перевірки.
- `compose.yaml`, `compose.production.yaml`, `deploy/` — конфігурація контейнерного розгортання.

Локальний запуск і перевірки: [docs/local-development.md](docs/local-development.md).
Підготовка VPS, HTTPS та резервування: [docs/deployment.md](docs/deployment.md).
Актуальні рішення: [PROJECT_MEMORY.md](PROJECT_MEMORY.md).
Повний контекст для іншої моделі, референси й актуальні вимоги: [MODEL_HANDOFF.md](MODEL_HANDOFF.md).

## Межі готовності

Наявність OAuth/Stripe коду не означає, що провайдери підключені. Потрібні їхні облікові записи, секрети та тестування живого сценарію. Локальні demo-реєстрація/оплата явно позначені й недоступні в production. Юридичні тексти — чернетки до внесення даних оператора та затвердження.

AI-аналіз, навчання моделей і методика тестових вправ — наступні етапи; сайт не видає симуляцію за реальне оцінювання.

## Попередні матеріали

`src/`, `public/`, кореневий `package.json` і Vite-конфігурація збережені як попередній React-концепт. Дизайн-пакети та дослідження — у `design-previews/`. Старий notes-app в іншій папці не змінюється.

Секрети ніколи не додаються до Git. `.local-tools/` і `.env` — локальні, виключені з версійного контролю.

Поточний сценарій акаунта, тріалів і тижневого прогресу: [account-and-membership.md](docs/account-and-membership.md). Основна реєстрація підтверджується кодом із листа; локальні demo API залишені для тестів.
