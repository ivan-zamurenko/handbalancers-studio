# OAuth для поточного Supabase-проєкту

Підтверджено власником 2026-10-20:
- Supabase: https://dwckvtuhgelhsbjyhpks.supabase.co
- Apple Developer account ще немає.
- Підключення провайдерів і реальний вхід ще не перевірено.

Для першої перевірки використовуємо локальний сайт http://127.0.0.1:8000.
Це тимчасова локальна адреса, не production deployment.

## 1. Google Cloud

Відкрити https://console.cloud.google.com/auth/overview у своєму Google account.
Вибрати або створити Cloud project для Studio. Заповнити Branding (назва,
контактний email), Audience (External; для testing додати свій email до test users),
Data Access (openid, email, profile). Платежі Google API для звичайного входу
цей застосунок не використовує.

Clients → Create client → Web application.
- Authorized JavaScript origin: `http://127.0.0.1:8000`
- Authorized redirect URI: `https://dwckvtuhgelhsbjyhpks.supabase.co/auth/v1/callback`

Зберегти Client ID та Client Secret у Supabase Google provider; у чат не копіювати.

## 2. Supabase

https://supabase.com/dashboard/project/dwckvtuhgelhsbjyhpks/auth/providers

У Google: увімкнути provider, внести Client ID/Secret, зберегти.
Authentication → URL Configuration:
- Site URL: `http://127.0.0.1:8000`
- Redirect URL: `http://127.0.0.1:8000/auth/callback`

Застосунок додає до callback query `attempt` і `provider`. При однаковому Site URL
origin Supabase дозволяє повернення з query; перевірити збереження query реальним
roundtrip. При переході на HTTPS staging оновити обидві адреси й allowlist.
Google повертається до Supabase callback, а Supabase — до локального callback.

## 3. Локальний сервер

`.env.local` підготовлено і виключено з Git; права доступу0600.
SUPABASE_URL/PUBLIC_ORIGIN задані, TOKEN_ENCRYPTION_KEY згенеровано локально.
Не перегенеровувати ключ під час звичайного перезапуску.
Заповнити лише локально:
- SUPABASE_PUBLISHABLE_KEY — publishable/anon key з Supabase API keys, не service_role.
- AUTH_DATABASE_URL — psycopg URL окремого DB login з правами studio_auth_runtime.
  Не postgres/migration_owner. Supabase auth і studio schema мають бути в тій самій БД.

Перед запуском потрібні product migrations до0006 на цьому новому проєкті
та окремий runtime login. Їх застосування до віддаленої БД ще не виконано:
потрібен підключений Supabase або захищене локальне з’єднання. Не запускати
міграції старого runtime. Без перевірки нової БД не позначати цей крок готовим.

Після налаштування Google, DB та ключів: OAUTH_GOOGLE_ENABLED=true.
OAUTH_APPLE_ENABLED=false до окремого налаштування Apple.
Зупинити попередній локальний preview через його термінал, потім з кореня:

```sh
uv run --env-file .env.local uvicorn studio.main:create_app --factory --host 127.0.0.1 --port 8000
```

Ця команда явно читає приватний файл. `tools/serve_preview.py` як і раніше
не підключає credentials. Після входу перевірити /api/session і logout.

## 4. Apple

Поки Apple Developer account відсутній, Apple лишається вимкненим.
Після отримання доступу потрібні primary App ID із Sign in with Apple,
Services ID для вебсайту, domain/return URL і signing key. Return URL:
`https://dwckvtuhgelhsbjyhpks.supabase.co/auth/v1/callback`.
Apple client secret зберігається в Supabase і поновлюється кожні6місяців.
Код не створює Apple account і не купує членство.

## Які дані зберігаються

- `auth.users` / `auth.identities`: Supabase веде identity, email (у тому числі
  Apple private relay) і metadata провайдера. Ці таблиці managed Auth не мігруємо.
- `studio.users.auth_user_id`: зв’язок із підтвердженою identity, без власного merge за email.
- `display_name`: full_name/name цілком; не вгадуємо прізвище з порядку слів.
- `first_name` / `last_name`: явні given_name/family_name або first_name/last_name,
  якщо вони є. Незаповнені (NULL) поля дозаповнюються при наступному вході.
- Наявні значення залишаються; role завжди задає сервер, не metadata.

Apple web OAuth не передає повне ім’я. Google може передати лише повне ім’я
без окремих first/last. Відсутні поля лишаються NULL, profile_complete=false.
Фото не копіюємо в product schema; якщо provider його передав, воно лишається
у managed metadata. Не створюємо дубль email чи нову таблицю credentials.

Офіційні джерела:
- https://supabase.com/docs/guides/auth/social-login/auth-google
- https://supabase.com/docs/guides/auth/social-login/auth-apple
- https://supabase.com/docs/guides/auth/redirect-urls
- https://github.com/supabase/auth/blob/master/internal/api/provider/oidc.go
- https://github.com/supabase/auth/blob/master/internal/utilities/request.go
