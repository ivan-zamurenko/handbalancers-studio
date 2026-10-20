# Поточний checkpoint — S03-05 завершено локально

Повернення до послідовного roadmap за запитом власника. S00–S02 завершені;
S03-01..05 done. Додаткові landing/UI/OAuth child cards не означають завершення S04/S05.
S03-04: справжній local Supabase confirmation email,6-digit OTP, JWT, product profile,
server session, replay/expiry rejection, rollback/retry, member-only role, resend quota.
31 auth integration +96 regression/16subtests GREEN; read-only review clean.
AUTH_EMAIL_ENABLED=false за замовчуванням, незалежний від social flags.
S03-05: password login, opaque cookie rotation, generic401, independent email flag,
origin guard, rate limits, no-store на всіх auth/session responses.
35 Auth integration +79 regression GREEN; read-only review clean.
Наступна картка: S03-06 — refresh singleflight/lease та atomic token swap.
Поточний commit/push/CI перевіряються після комміту; попередній5096510 pushed,CI39427618056 green.

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
Parents S03/S04 не завершені; core next S03-06. Session refresh/profile completion і підключення login UI ще не готові. Preview навмисно не підключає credentials.

Гілка task/execution-v4; origin ivan-zamurenko/handbalancers-studio.
Preview PID23006 port8000. User docs deletions, .vscode, Copilot files не чіпати.
Запуск preview: uv run --locked python tools/serve_preview.py.
Тести: PATH .local-tools/uv-env/bin і .local-tools/node/bin; UV_CACHE_DIR=.local-tools/uv-cache.
DB: DOCKER_HOST=unix://$HOME/.colima/studio-s01/docker.sock; unset DOCKER_CONTEXT.
uv run --locked python -m tools.check_migrations. Не --fresh на існуючій БД.
