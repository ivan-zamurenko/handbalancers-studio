# Локальна розробка нового сайту

Новий застосунок живе в `server/`. React/Vite у `src/` — збережений попередній концепт; він не є сервером нового сайту.

## Поточне локальне середовище

- Python 3.13: `.local-tools/python` (ізольоване оточення).
- PostgreSQL 14.19 із уже встановленого Homebrew: окремий кластер `.local-tools/postgres/data`, порт **55432**, доступ тільки з localhost, SCRAM-пароль.
- `studio` — локальні дані, `studio_test` — окрема тестова база. Інші встановлені бази не використовуються.
- Конфігурація: `server/.env`, права 0600, виключена з Git. Не показувати її в чаті чи логах.
- Застосунок: http://127.0.0.1:8000.

Локальний PostgreSQL 14 використано тому, що він уже встановлений. Docker-розгортання описане окремо в deployment.md; контейнерну версію БД потрібно перевірити перед production. Docker на поточному комп’ютері не виявлено.

## Запуск

З кореня репозиторію:

```sh
python3 scripts/local.py db-status
python3 scripts/local.py db-start
python3 scripts/local.py migrate
python3 scripts/local.py serve
```

`db-start` потрібен лише якщо кластер зупинений. `serve` працює у foreground; Ctrl+C зупиняє API. Окремо зупинити тільки проєктну БД:

```sh
python3 scripts/local.py db-stop
```

## Перевірки

```sh
python3 scripts/local.py test
.local-tools/python/bin/python -m ruff check server/studio server/tests scripts/local.py
.local-tools/node/bin/node scripts/check-site.mjs
```

Тести БД працюють лише з окремою `studio_test`; production-БД не використовувати. Браузерна перевірка потребує запущеного API на порту 8000, наявних Playwright/axe з кореневого package.json та Chrome. Вона використовує окремий браузерний контекст і створює демонстраційний профіль у локальній `studio`. Скриншоти та JSON-звіт зберігаються у `.local-tools/verification/site/`.

Для нового комп’ютера контейнерний запуск описаний у `docs/deployment.md`; нативний demo-сценарій перевірений тут окремо. Не копіюйте паролі та локальний data directory в інші середовища.

## Чесні межі локального режиму

Google/Apple/Stripe вмикаються лише з налаштованими credentials. Локальний режим дозволяє окремий явно позначений demo-акаунт і demo-оплату, щоб перевірити сайт та збереження в PostgreSQL. Це не підтвердження живих інтеграцій. У production цей режим заборонений конфігурацією та серверними перевірками.

Оцінювання вправ, реальні навчальні програми й AI ще не входять у реалізацію сайту. Кабінет має показувати їхній фактичний стан, не вигадані результати.

Актуальна реєстрація й приватна локальна скринька описані в [account-and-membership.md](account-and-membership.md). Для листів: `python3 scripts/open-local-mail.py`. Наскрізний сценарій: `.local-tools/node/bin/node scripts/check-account-flow.mjs`.
