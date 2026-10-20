# Google та Apple: налаштування нового проєкту

Конкретні адреси й кроки для проєкту власника: [oauth-project-setup.md](oauth-project-setup.md).

Стан: код OAuth PKCE підготовлено; провайдери ще не налаштовані власником.
Реальні Google/Apple roundtrips не перевірено. Локальні тести використовують
справжню PostgreSQL і підписані тестові JWT, але синтетичний upstream.
Email/password форма залишається preview. Managed identity належить Supabase.

## Google

У Google Auth Platform створіть OAuth client типу Web application, налаштуйте
назву продукту, consent screen та test users. Для входу достатньо openid, email,
profile. Authorized redirect URI — callback **Supabase**, взятий з його Dashboard
(звичайно `https://<project-ref>.supabase.co/auth/v1/callback`).
У Supabase Authentication → Providers → Google увімкніть провайдера та внесіть
Client ID / Client Secret. Не надсилайте секрети в чат і не додавайте їх до Git.

Офіційні кроки: https://supabase.com/docs/guides/auth/social-login/auth-google

## Apple

Потрібен Apple Developer account із Sign in with Apple, primary App ID,
Services ID для вебвходу, verified domain і return URL Supabase.
У Supabase Apple provider внесіть Services ID та згенерований Apple client secret.
Ключ Apple .p8 зберігайте поза репозиторієм. Для web OAuth secret потребує
поновлення щонайменше кожні 6 місяців; заведіть операційне нагадування.
Apple може не передати ім’я; не підставляйте вигадане. Наш профіль тоді incomplete.
Email relay не використовується для самостійного об’єднання акаунтів.

Офіційні кроки: https://supabase.com/docs/guides/auth/social-login/auth-apple

## Повернення до застосунку

Supabase URL Configuration: Site URL = довірений PUBLIC_ORIGIN.
Додайте callback застосунку `/auth/callback` на цьому origin до redirect allowlist,
з підтримкою query-параметрів `attempt` і `provider`; не дозволяйте чужі origins.
Це інший callback, ніж callback Supabase у Google/Apple. Після повернення
застосунок перевіряє браузер і одноразову спробу, обмінює code через PKCE,
створює member profile і серверну session. Дозволений return path наразі `/plans`.

https://supabase.com/docs/guides/auth/redirect-urls
https://supabase.com/docs/guides/auth/sessions/pkce-flow

## Серверне середовище

Змінні з `.env.example` треба передати процесу явно; .env автоматично не читається.

- SUPABASE_URL — origin нового Supabase-проєкту.
- SUPABASE_PUBLISHABLE_KEY — publishable/anon key (не service-role).
- PUBLIC_ORIGIN — точний origin сайту; staging/production лише HTTPS.
- TOKEN_ENCRYPTION_KEY — 32 випадкові байти у стандартному Base64, зберігати стабільно.
- AUTH_DATABASE_URL — окремий LOGIN із membership studio_auth_runtime,
  без migration_owner, власності schemas/tables, SUPERUSER/BYPASSRLS/CREATEROLE.
- OAUTH_GOOGLE_ENABLED / OAUTH_APPLE_ENABLED — true лише після налаштування
  відповідного провайдера; спочатку перевірити на ізольованому staging.

Перед запуском застосувати міграції до нової БД через окремий migration operator.
Runtime не робить міграцій і не підвищує DB privileges. Поточний head 0006.
`tools/serve_preview.py` навмисно не читає provider credentials. Для налаштованого
runtime: `uv run uvicorn studio.main:create_app --factory --host 127.0.0.1 --port 8000`.
Не використовувати тестові DB passwords у staging.

## Що перевірити після налаштування

Для кожного провайдера: успіх, скасування, повтор callback, інший браузер,
повернення до /plans, reload із session і logout. Перевірити Apple без імені,
relay email, повторний вхід і строк чинності secret. Лише після цього gate
G_AUTH_PROVIDERS можна позначити passed для конкретного провайдера.

Сесія наразі закінчується разом із access JWT; автоматичний refresh — окрема
незавершена S03-06. Авторизація не відкриває paid доступ. Profile completion,
email verification/password login і повний onboarding залишаються у roadmap.
Локальний вихід відкликає cookie негайно; збій Supabase logout цього не скасовує.
OAuth start: 10 спроб за хвилину на IP через DB quota; за reverse proxy потрібне
окремо налаштоване довірене визначення адреси (X-Forwarded-For тут не довіряємо).

Автозаповнення профілю: після JWT/UUID перевірки переносимо full_name/name
у display_name, окремі first/last — лише за явними полями. Заповнюємо NULL,
зберігаємо ручні значення й ролі. Email належить managed auth.users.
