# Поточний checkpoint

S01-03 завершено: command_transaction створює Session/транзакцію та задає
studio.user_id через параметризований set_config(..., true). Actor — UUID із
довіреної серверної автентифікації; auth ще не підключено.
База комміту: 53e838e6d469283482b76c0364df667f0df406a3. Push/CI перевіряються після commit.

45 backend-тестів GREEN, включно з 8 новими випадками справжнього RLS,
commit/rollback, pool reuse та двома одночасними транзакціями. Ruff/format і
mypy server/studio GREEN; read-only review без блокерів.
Evidence: .workflow/evidence/S01-03.json.

У робочому дереві до цієї задачі видалено docs/*. Ці видалення й Copilot-файли
не змінено та не включено в комміт. Через них локальний roadmap validate падає;
контракти прочитані з HEAD. Повний робочий checkout не оголошується GREEN.

## Попередній checkpoint S01-02

S01-02 завершено локально: Alembic baseline створює studio/studio_private та
мінімальні ролі; managed auth/storage/realtime не змінюються. Проєкт у корені,
гілка task/execution-v4; origin — ivan-zamurenko/handbalancers-studio.
База перед коммітом: 920dae911d9bfdd632a88f97747115b06a83dc26. SHA комміту й push
зафіксувати у звіті після комміту.

## Перевірено

- S01-02 checks: PostgreSQL integration — 6 passed; local-stack unittest — 21 passed;
  Ruff, scoped mypy та `uv lock --check` пройшли. Evidence: `.workflow/evidence/S01-02.json`.
- TDD caveat: implementation і тести вже були в незакомміченій копії під час resume;
  попередній поведінковий RED не зафіксований. Guarded запуск знайшов thread-unsafe
  Alembic API в harness; перевірку виправлено на два окремі CLI-процеси.

- S01-01: 19 unittest-тестів; pytest також GREEN.
- Affected suite: 83 тести, 24 subtests; наявний Starlette warning не приховано.
- Ruff та mypy для нового коду GREEN; mypy потребує --explicit-package-bases.
- dev/test мають різні project_id, порти, workdirs, реальні контейнери та volumes.
- Окремі studio_local_dev/test: власні паролі працюють, чужі відхиляються.
- Логіни без superuser/createdb/createrole/inherit/replication/bypassrls; auth.users читати не можуть.
- Два одночасні повторні provisioning та два guarded test runs зберігають dev/test sentinels.
- Реальні HTTP JWT-перевірки: власний токен 200, чужий 401 в обох напрямках.
- Guard перевіряє URL, Docker socket, project label, container/volume name та порт.
- Прямий fixture-guard відхиляє PG* overrides; runner очищує їх перед запуском.
- Test runner не запускає/не скидає БД; S01-02 додає тільки schema/role baseline.
- Read-only review: PGHOSTADDR bypass виправлено; негативні endpoint-тести незалежні від username guard.
- Supabase CLI 2.120.0 встановлено в .local-tools/supabase-cli, ES256 генерація працює.
- Docker server 29.5.2 у Colima studio-s01, 4 CPU/6 GiB/40 GiB. Обидва профілі працюють.
- RED/GREEN та погоджені виправлення помилкових тестових припущень: .workflow/evidence/S01-01.json.

## Наступний крок

S01-04: наступна картка roadmap; прочитати її та релевантний контракт перед тестами.
Службовий auth лишається під керуванням Supabase, без подвійного DDL.
Локальне середовище для DB-команд:

```sh
export PATH="$PWD/.local-tools/supabase-cli/node_modules/.bin:/opt/homebrew/bin:$PATH"
export DOCKER_HOST="unix://$HOME/.colima/studio-s01/docker.sock"
unset DOCKER_CONTEXT
uv run --locked python tools/local_stack.py start dev
uv run --locked python tools/local_stack.py start test
python tools/local_stack.py provision-migrations test
python tools/local_stack.py test -- uv run --locked pytest server/tests/integration/database/test_migration_baseline.py -q
uv run --locked --with 'psycopg[binary]==3.3.3' python -m tools.tests.test_s01_01_local_supabase --live
```

SUPABASE_DB_PASSWORD не працює для local CLI. Окремі DB-логіни створюються
через перевірений container ID і локальну bootstrap-роль supabase_admin.
Hosted provisioning виконується окремо операторським шляхом; baseline не змінює
managed Supabase roles.
Ключі не друкувати; .local-tools/supabase містить приватні локальні файли.
Supabase може публікувати Docker-порти на всіх інтерфейсах: guard URL не є firewall.
Реальні Google/Apple/email flows ще не перевірені й належать наступним auth-карткам.

## Домовленості

Старий runtime не використовувати й не відновлювати. Усе створювати в корені.
Основна гілка task/execution-v4; стару main видалено, історію збережено під
archive/pre-execution-v4. Не створювати окремий проєкт/worktree.
