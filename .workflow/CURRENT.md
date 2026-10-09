# Поточний checkpoint

S01-05 завершено: RLS/column grants профілю та приватна provision_member.
База перед коммітом: 54dc897f36f7b7ae66c81a9ab66724428e49daa5 (S01-04 запушено, CI GREEN).
Проєкт у корені, task/execution-v4; origin ivan-zamurenko/handbalancers-studio.
SHA/push/CI перевіряються після commit; evidence зберігає pending_at_commit.

## Перевірено

- 73 backend-тести, включно з 20 security cases; Ruff/format/mypy GREEN.
- studio_web читає лише свій active profile, зокрема coach не отримує загальний доступ.
- UPDATE лише first_name/last_name/locale/timezone; чужі рядки й inactive недоступні.
- id/auth_user_id/role/is_active/system columns, INSERT/DELETE/TRUNCATE закриті.
- anon/authenticated не мають schema/table/function доступу.
- studio_auth_runtime має лише EXECUTE provision_member, без прямих table grants.
- Provision завжди створює member, ігнорує metadata; repeat не змінює існуючий профіль.
- Concurrent provision/edits, rollback, temp-table/search_path атака перевірені.
- 0003 upgrade/repeat на справжньому test Supabase: auth schema незмінна, grants правильні.
- Read-only review без блокерів. RED/GREEN: .workflow/evidence/S01-05.json.
- User docs deletions/Copilot additions недоторкані й поза коммітом. Локальний
  roadmap validate через відсутні docs не GREEN; контракти прочитані з HEAD.

## Наступний крок

S01-06 — прочитати картку roadmap перед тестами.
Підтвердження provider identity є передумовою приватного provision; auth service
впроваджується в S03-04, HTTP auth зараз не підключено.
Provision SECURITY DEFINER належить non-superuser migration_owner, має fixed
search_path та schema-qualified SQL. GUC actor надходить лише з trusted backend.
Timestamp/version editing та IANA timezone validation ще не реалізовані.
Baseline/profile-schema suites закріплені за 0001/0002; security suite тестує head.

## Локальний стенд

Docker server у Colima studio-s01; окремі dev/test Supabase profiles та credentials.
Test PostgreSQL 127.0.0.1:55322, HTTP 55321. Реальний test DB вже має revision 0003.
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
