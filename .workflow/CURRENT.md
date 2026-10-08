# Поточний checkpoint

S01-01 завершено: реальна ізоляція dev/test перевірена на двох локальних Supabase.
Проєкт у корені, гілка task/execution-v4; origin — ivan-zamurenko/handbalancers-studio.
Попередній checkpoint: 613fa6f. SHA follow-up комміту й push — у звіті після комміту.

## Перевірено

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
- Test runner не запускає/не скидає БД. Product DDL ще немає.
- Read-only review: PGHOSTADDR bypass виправлено; негативні endpoint-тести незалежні від username guard.
- Supabase CLI 2.120.0 встановлено в .local-tools/supabase-cli, ES256 генерація працює.
- Docker server 29.5.2 у Colima studio-s01, 4 CPU/6 GiB/40 GiB. Обидва профілі працюють.
- RED/GREEN та погоджені виправлення помилкових тестових припущень: .workflow/evidence/S01-01.json.

## Наступний крок

S01-02: Alembic baseline для studio/studio_private. Картку ще не розпочато.
Службовий auth лишається під керуванням Supabase, без подвійного DDL.
Локальне середовище для DB-команд (додатково до docs/toolchain-lock.md):

```sh
export PATH="$PWD/.local-tools/supabase-cli/node_modules/.bin:/opt/homebrew/bin:$PATH"
export DOCKER_HOST="unix://$HOME/.colima/studio-s01/docker.sock"
unset DOCKER_CONTEXT
uv run --locked python tools/local_stack.py start dev
uv run --locked python tools/local_stack.py start test
uv run --locked --with 'psycopg[binary]==3.3.3' python -m tools.tests.test_s01_01_local_supabase --live
```

SUPABASE_DB_PASSWORD не працює для local CLI. Окремі DB-логіни створюються
через перевірений container ID і локальну bootstrap-роль supabase_admin.
Managed ролі не змінюються; міграційних чи runtime-прав ці логіни ще не мають.
Ключі не друкувати; .local-tools/supabase містить приватні локальні файли.
Supabase може публікувати Docker-порти на всіх інтерфейсах: guard URL не є firewall.
Реальні Google/Apple/email flows ще не перевірені й належать наступним auth-карткам.

## Домовленості

Старий runtime не використовувати й не відновлювати. Усе створювати в корені.
Основна гілка task/execution-v4; стару main видалено, історію збережено під
archive/pre-execution-v4. Не створювати окремий проєкт/worktree.
