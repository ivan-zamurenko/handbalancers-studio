# Поточний checkpoint — 2026-10-19

Явний запит: компонування login і Google/Apple OAuth.
S03-10b commit 93c7836: дії пароля в одному рядку, submit по центру; 8 browser GREEN.
S04-01a: серверний PKCE, real DB спроби/сесії, member provision, current profile,
CSRF logout, DB rate limit;12 OAuth DB +60 DB regression GREEN. Міграція0005.
Review owner-role guard і CI coverage виправлено. Новий integration/auth включено в CI.
G_AUTH_PROVIDERS env_blocked: власник підтвердив, що Google/Apple не налаштовані.
Runtime flags false, credentials відсутні. Не називати live OAuth готовим.
Інструкція docs/oauth-setup.md, preview навмисно не читає credentials.
Session завершується разом із JWT; refresh/profile completion/email входу ще немає.
Далі UI кнопок/повідомлень/виходу, потім push і CI.
Батьківські S03/S04 залишаються todo; основний наступний крок S03-04.
Гілка task/execution-v4; origin ivan-zamurenko/handbalancers-studio.
Власні preview PID23006, port8000; не зупиняти сторонні процеси.
User docs deletions, .vscode та Copilot файли не чіпати.

Запуск preview: uv run --locked python tools/serve_preview.py (див .workflow/LOCAL_PREVIEW.md).
Для тестів PATH .local-tools/uv-env/bin і .local-tools/node/bin;
UV_CACHE_DIR=.local-tools/uv-cache, PLAYWRIGHT_BROWSERS_PATH=.local-tools/playwright-browsers.
DB: DOCKER_HOST=unix://$HOME/.colima/studio-s01/docker.sock; unset DOCKER_CONTEXT;
uv run python -m tools.check_migrations. Не використовувати --fresh на існуючій БД.
