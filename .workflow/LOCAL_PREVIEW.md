# Локальний перегляд

Запуск із кореня без ключів, БД та викликів зовнішніх провайдерів:

```sh
uv run --locked python tools/serve_preview.py
```

Сервер слухає лише `127.0.0.1:8000`. Відкрити `/`, `/plans`, `/login`,
`/register`, `/verify-email` або `/recovery`. Email/Google в цьому режимі
не підключені; реєстрація та вхід не виконуються.

Збережені дизайн-варіанти лежать у `tools/previews/handstand/`:
- `/_previews/handstand/index.html` — п’ять варіантів;
- `/_previews/handstand/cycle.html` — фінальний цикл окремо для перегляду.

Ці шляхи монтує лише локальний інструмент і тестовий harness. Звичайний
`studio.main:create_app` їх не публікує. Робочий індикатор завантаження
використовує `server/static/js/components/handstand-motion.js`.

Для налаштованого сайту з Auth використовуйте окремий запуск:

```sh
uv run --locked --env-file .env.local uvicorn studio.main:create_app --factory --host 127.0.0.1 --port 8000
```

Не запускайте обидва процеси на одному порту. Зупинка — Ctrl+C.
Не перегенеровуйте наявні ключі для звичайного перезапуску.
Поточні зовнішні gates і наступна картка: [CURRENT.md](CURRENT.md).
