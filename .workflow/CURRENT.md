# Поточний checkpoint

S01-07 реалізовано локально: окремий database CI job та migration gate.
База комміту: 04237ac0272feaa347557187ac1a2d611d7eca7c (S01-06 push/CI GREEN).
Гілка task/execution-v4, origin ivan-zamurenko/handbalancers-studio, усе в корені.
Фактичний fresh GitHub CI перевіряється після push; до того remote_ci=pending.

## Перевірено

- uv run --locked python -m tools.check_migrations: single linear head 0004,
  40 integration + 20 security DB-тестів; окремі suite processes, жодних skip/xfail.
- 12 tooling tests; Ruff/format і mypy checker GREEN.
- --fresh на наявному локальному test DB відмовив до змін, без reset.
- --fresh CI вимагає порожні product schemas, existing managed auth.users,
  upgrade/repeat, незмінні managed definitions, ORM parity та runtime grants/RLS.
- Supabase CLI 2.120.0 через verified setup-cli v3.0.1 SHA; secrets не друкуються.
- Cleanup лише test workdir ephemeral CI runner; ніяких dev/hosted операцій.
- Read-only review без блокерів. Evidence: .workflow/evidence/S01-07.json.
- Recovery: .workflow/MIGRATION_RECOVERY.md.
- User docs deletions/Copilot additions не змінено й не staged. Через відсутні
  docs локальний roadmap validate не GREEN; контракти прочитані з HEAD.

## Наступний крок

S02-01: прочитати наступну картку після підтвердження fresh CI.
Звичайна локальна migration gate: uv run --locked python -m tools.check_migrations.
--fresh призначено для нового test stack, не для його очищення.
Сховище S01-06 не є повною автентифікацією; HTTP auth/provider/key-loader ще не підключено.
External exchange можливий лише після commit consume_attempt.

## Локальний стенд

Docker server у Colima studio-s01; окремі dev/test Supabase profiles та credentials.
Test PostgreSQL 127.0.0.1:55322, HTTP 55321. Реальний test DB вже має revision 0004.
Managed Auth лишається під керуванням Supabase; Alembic лише studio/studio_private.

    export PATH="$PWD/.local-tools/uv-env/bin:$PWD/.local-tools/supabase-cli/node_modules/.bin:/opt/homebrew/bin:$PATH"
    export UV_CACHE_DIR="$PWD/.local-tools/uv-cache"
    export DOCKER_HOST="unix://$HOME/.colima/studio-s01/docker.sock"
    unset DOCKER_CONTEXT
    uv run --locked python tools/local_stack.py test -- uv run --locked pytest server/tests/integration/database -q

Після нового provision потрібен tools/local_stack.py provision-migrations test:
він створює приватний migration_owner та мінімальні REFERENCES grants.
Hosted provisioning виконується окремо оператором, не міграцією.
Ключі не друкувати; .local-tools/supabase містить приватні локальні файли.
Test guard не є firewall. Google/Apple/email flows не перевірені.

## Домовленості

Старий runtime не використовувати й не відновлювати. Усе створювати в корені.
Основна гілка task/execution-v4; стару main видалено, історію збережено під
archive/pre-execution-v4. Не створювати окремий проєкт/worktree.
