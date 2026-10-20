# Поточний checkpoint — 2026-10-20

S04-02a: OAuth profile import, міграція0006. Заповнення лише NULL після JWT/UUID
перевірки; fullname цілком, explicit first/last, server member role. 82 DB +75
non-DB GREEN, lint/types GREEN, read-only review без блокерів.
Evidence: .workflow/evidence/S04-02a.json. Commit/push перевіряються після комміту.
Попередній f75e91b pushed; CI39274925444 success.

Supabase підтверджено: https://dwckvtuhgelhsbjyhpks.supabase.co.
Apple Developer account немає. G_AUTH_PROVIDERS env_blocked: remote migrations,
Google config і live roundtrip ще не виконані; Apple вимкнений.
Наступний крок: підключення Supabase для перевірки нової БД та Google Client ID/Secret
у dashboard провайдера. Інструкція docs/oauth-project-setup.md.
Приватний ignored .env.local0600 має URL і generated encryption key; publishable key
та AUTH_DATABASE_URL ще порожні. Не друкувати/перегенеровувати секрети.
Локальний origin127.0.0.1:8000 — припущення для першої перевірки.
Parents S03/S04 todo; core next S03-04. Session refresh/profile completion/email
login ще не готові. Preview навмисно не підключає credentials.

Гілка task/execution-v4; origin ivan-zamurenko/handbalancers-studio.
Preview PID23006 port8000. User docs deletions, .vscode, Copilot files не чіпати.
Запуск preview: uv run --locked python tools/serve_preview.py.
Тести: PATH .local-tools/uv-env/bin і .local-tools/node/bin; UV_CACHE_DIR=.local-tools/uv-cache.
DB: DOCKER_HOST=unix://$HOME/.colima/studio-s01/docker.sock; unset DOCKER_CONTEXT.
uv run --locked python -m tools.check_migrations. Не --fresh на існуючій БД.
