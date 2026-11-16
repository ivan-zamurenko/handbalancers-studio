# Auth: точный первый пользовательский вертикальный срез

## UI
`/register`: имя, фамилия, email, password, показать/скрыть пароль, доступная ошибка, submit pending, ссылка на login. Social кнопки только для действительно сконфигурированных провайдеров. Нет кнопки «Supabase».
`/verify-email`: email, 6-значный code, resend с cooldown, исправить email, ошибки expiry/invalid/generic. Не сохранять password в storage.
`/login`: email/password, recovery, налаштований Google. Apple видалено з продукту (рішення власника 2026-11-16). OAuth возвращается в тот же onboarding/plan path.
`/complete-profile`: для verified OAuth без имени; завершение до Checkout, не выдумывать identity.
`/recovery`: запрос и подтверждение по upstream flow, не обычная paid session.

## Статусы
`guest → verification_pending → authenticated_incomplete|authenticated → inactive_or_paid_access`.
Identity authenticated не означает paid. Profile incomplete не означает unverified. Тема не влияет на Auth. Supabase pending `auth.users` до verification допустима; `studio.users` создаётся только из подтверждённой identity. Различие описано открыто, не маскируется обещанием «в БД вообще нет пользователя».

## Payloads
`POST /api/auth/register`: {first_name,last_name,email,password}. Response 202 {state:"verification_pending"}. 422 для невалидного ввода до provider. Существующий email — нейтральное допустимое сообщение. Provider unavailability 503, rate limit 429; ни в одном отказе authenticated cookie не выдаётся.
`POST /api/auth/verify-email`: {email,token}. Реальный Supabase verification, затем одна provision операция и local session.
`POST /api/auth/login`: {email,password}. Verified identity, profile UUID, rotation cookie.
`GET /api/session`: {authenticated,user:{id,first_name,last_name,role,locale,timezone,profile_complete},entitlements,csrf_token}. Нет access/refresh/provider secrets. Для guest возвращается ограниченное состояние по API контракту; protected API всё равно 401.
`POST /api/auth/logout`: CSRF, revoke local, clear cookie; upstream failure не оставляет local active.
`POST /api/auth/oauth/{provider}/start`: allowlist лише google (Apple видалено 2026-11-16; CHECK у БД з 0004 ще допускає 'apple', застосунок його не записує), trusted callback allowlist и browser-bound attempt. PKCE verifier изолирован, Supabase owns upstream OAuth state. App correlation token не подменяет state Supabase.
`GET /auth/callback`: code+app attempt, browser binding/expiry/consumption проверены до code exchange. Auth code не сохраняется в logs.

## Сессии
Cookie opaque random token; хранить только hash. Upstream tokens/verifier — AEAD encrypted + key_id для rotation, associated data с ID записи. Trusted actor строится после local revoke/expiry + JWT signature/issuer/audience/expiry + profile.is_active/current role. Upstream validation на login/refresh/критических операциях; обычный cache TTL явно зафиксирован и протестирован. Не утверждать мгновенный revoke внешней provider session на основании одной подписи JWT.

Request-scoped SDK client или stateless HTTP gateway. Глобальный mutable Supabase client с user session недопустим. Refresh singleflight/lease одного session, bounded timeout, atomic token swap; не долгий глобальный lock. Ошибка identity linking не лечится собственным merge по email. Auth UUID — identity key.

## Таблицы
users, user_preferences, onboarding_profiles; private web_sessions/auth_attempts/auth_rate_limits. Никаких собственных passwords/identities в product tables. Managed auth.users не дропать/не пересоздавать Alembic.

## Доказательства готовности
Unit fake Gateway проверяет поведение приложения. Local Supabase roundtrip проверяет email/managed auth/provision. Google потребує окремої реальної перевірки. Наявність кнопки, SDK виклику або зеленого mock тесту не підтверджує provider readiness. Apple виключено поточним рішенням власника; relay/відсутнє ім’я/secret expiry [S-APPLE] застосовуються лише після окремого рішення повернути інтеграцію.

## Scope auth commits
S03-01..11 + S04-01..06. Каждый с отдельным тестом/коммитом. Не объединять всё в «implement authentication». Root DB/CI/UI подготовлены раньше, потому что без них нельзя честно получить и проверить RED/GREEN.
