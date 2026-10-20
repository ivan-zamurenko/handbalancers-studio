# Поточний checkpoint — S03-04 завершено локально

Повернення до послідовного roadmap за запитом власника. S00–S02 завершені;
S03-01..04 done. Додаткові landing/UI/OAuth child cards не означають завершення S04/S05.
S03-04: справжній local Supabase confirmation email,6-digit OTP, JWT, product profile,
server session, replay/expiry rejection, rollback/retry, member-only role, resend quota.
31 auth integration +96 regression/16subtests GREEN; read-only review clean.
AUTH_EMAIL_ENABLED=false за замовчуванням, незалежний від social flags.
Наступна картка: S03-05 — email/password login + protected cookie.
Поточний commit/push/CI перевіряються після комміту; попередній d922c48 pushed,CI39425114231 green.

AUTH_DATABASE_URL — PostgreSQL connection string окремого restricted LOGIN, не API key.
Таблиці локально вже створені міграціями0001–0006. Хмарний Supabase ще не мігрований;
remote role/bootstrap не виконано, не називати підключення готовим.
Інструкція docs/oauth-project-setup.md оновлена з поясненням Connect/runtime LOGIN.

Supabase підтверджено: https://dwckvtuhgelhsbjyhpks.supabase.co.
Apple Developer account немає. G_AUTH_PROVIDERS env_blocked: remote migrations,
Google config і live roundtrip ще не виконані; Apple вимкнений.
Окремий environment gate: підключення Supabase для перевірки нової БД та Google Client ID/Secret
у dashboard провайдера. Інструкція docs/oauth-project-setup.md.
Приватний ignored .env.local0600 має URL і generated encryption key; publishable key
та AUTH_DATABASE_URL ще порожні. Не друкувати/перегенеровувати секрети.
Локальний origin127.0.0.1:8000 — припущення для першої перевірки.
Parents S03/S04 не завершені; core next S03-05. Session refresh/profile completion/email
login ще не готові. Preview навмисно не підключає credentials.

Гілка task/execution-v4; origin ivan-zamurenko/handbalancers-studio.
Preview PID23006 port8000. User docs deletions, .vscode, Copilot files не чіпати.
Запуск preview: uv run --locked python tools/serve_preview.py.
Тести: PATH .local-tools/uv-env/bin і .local-tools/node/bin; UV_CACHE_DIR=.local-tools/uv-cache.
DB: DOCKER_HOST=unix://$HOME/.colima/studio-s01/docker.sock; unset DOCKER_CONTEXT.
uv run --locked python -m tools.check_migrations. Не --fresh на існуючій БД.
