# Поточний checkpoint

S01-04 завершено: модель User та міграція 0002 для studio.users.
База перед коммітом: ea472b58eebfd175f6de0aba0d61ba8c15f9264f (S01-03 запушено, CI GREEN).
Проєкт у корені, task/execution-v4, origin ivan-zamurenko/handbalancers-studio.
SHA/push/CI S01-04 перевіряються після commit; evidence зберігає pending_at_commit.

## Перевірено

- 53 backend-тести, з них 8 нових profile та 14 попередніх DB; 21 tooling unittest.
- UNIQUE auth_user_id витримує дві одночасні вставки; FK, role/locale та row_version constraints.
- OAuth names nullable; locale/timezone задаються явно; role default member.
- Alembic/model parity без auth у product MetaData; migration_owner не володіє managed Auth.
- На реальному test Supabase upgrade/repeat до 0002: FK правильний, auth OID/columns незмінні.
- Оператор отримує лише USAGE auth та REFERENCES(id), без SELECT/DML auth.users.
- Нова таблиця має RLS та закриті runtime grants до S01-05.
- Ruff/format/mypy GREEN; read-only review без блокерів.
- RED/GREEN/межі: .workflow/evidence/S01-04.json. Starlette warning не приховано.
- User docs deletions/Copilot additions залишено недоторканими й поза коммітом.
  Через відсутні docs локальний roadmap validate падає; контракти прочитано з HEAD.

## Наступний крок

S01-05 — profile security: RLS та column grants. Прочитати відповідну картку.
Auth endpoints, timezone validation та команди редагування профілю ще не реалізовані.
S01-03 command_transaction задає studio.user_id лише на одну транзакцію.
Baseline тести закріплено за 0001; profile suite перевіряє актуальний head.

## Локальний стенд

Docker server у Colima studio-s01; окремі dev/test Supabase profiles та credentials.
Test PostgreSQL 127.0.0.1:55322, HTTP 55321. Реальний test DB вже має revision 0002.
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
