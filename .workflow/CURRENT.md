# Поточний checkpoint

S01-06 завершено: private auth storage, моделі й міграція 0004.
База комміту: 0d406f2ae2ee8a5d12649ccf47367d4f0e68cf58 (S01-05 push/CI GREEN).
Гілка task/execution-v4, origin ivan-zamurenko/handbalancers-studio, усе в корені.
SHA/push/CI перевіряються після commit; evidence зберігає pending_at_commit.

## Перевірено

- 91 backend-тест; 18 storage cases із реальним PostgreSQL та AES-GCM.
- Cookie/state/browser-binding — випадкові 256-bit значення, у БД лише SHA256.
- Access/refresh/verifier — AES-256-GCM через cryptography 50.0.2; key_id/version
  та row/owner/provider/binding/expiry context автентифіковані.
- Explicit in-memory keyring; ключі не записуються в БД/Git. Old-key decrypt перевірено.
- Підміна/перенесення ciphertext, revoke/expiry, wrong browser/provider, replay,
  concurrent consume, rollback та обмежені grants перевірено.
- Expiry tests чекають справжнього завершення TTL, без зміни ciphertext/AAD.
- Read-only review без блокерів після цього виправлення.
- mypy/Ruff/format/lock checks GREEN; відомий Starlette warning лишається.
- Actual test Supabase upgrade/repeat до 0004: Auth незмінний, grants/RLS правильні.
- Evidence: .workflow/evidence/S01-06.json.
- Наявні user docs deletions/Copilot additions не змінено й не включено в commit;
  локальний roadmap validate через відсутні docs не GREEN. Контракти читалися з HEAD.

## Межа реалізації та наступний крок

S01-07: прочитати картку перед тестами.
TokenStore працює в caller-owned транзакції; COMMIT consume обов'язковий перед
майбутнім external code exchange. NOWAIT не чекає чужого row lock без обмежень.
read_session перевіряє лише local expiry/revoke, не JWT/current profile/provider.
HTTP auth/refresh/cookie endpoints і key-loader до застосунку ще не підключені.
Ключі передаються в TokenCipher(active_key_id, mapping_of_32_byte_keys).
AuthAttempt user_id може бути NULL до входу; WebSession user_id — NOT NULL FK.
Draft JSON не додавався наперед; store не приймає passwords/onboarding payload.
Auth runtime має лише SELECT/INSERT названих private tables та UPDATE
revoked_at/consumed_at. Ширші refresh/cleanup grants додаються з командою.
Historical profile schema parity звужено до users; storage suite перевіряє всі head models.

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
