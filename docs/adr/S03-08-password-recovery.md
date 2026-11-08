# S03-08 — одноразове підтвердження відновлення пароля

2026-11-08. Локальна реалізація; hosted readiness окремо.

## Контракт

- POST /api/auth/recovery/request {email} → 202 recovery_pending для відомої,
  невідомої, непридатної для recovery пошти й provider email cooldown. Мережеві
  помилки →503; локальний quota →429. Наявність акаунта не розкриваємо.
- POST /api/auth/recovery/confirm {email,token,password}: 6 цифр, пароль8–256;
  тільки same Origin, no-store, без секретів у URL/storage/logs. Успіх200
  {state:password_changed,login_required:true}; cookie лише видаляється.
- OTP через Supabase POST /verify type=recovery; отримані JWT перевіряються
  локальним validator, sub звіряється з user.id. Tokens лише в пам’яті сервера.
  Recovery не викликає accept_identity і не створює web_session.
- До PUT /user і після required global logout відкликаємо committed local sessions
  verified користувача. Existing provision_member grant дає mapping також inactive
  профілю; якщо профілю ще немає, створюється мінімальний member(uk,UTC), без сесії.
  Існуючі роль, активність і профіль не змінюються. Інші користувачі не зачіпаються.
- Немає schema/grant changes. Core deadline20s; фінальні DB revoke/local upstream
  cleanup виконуються поза deadline, з наявними DB/network limits. Password PUT
  не повторюємо автоматично; після невизначеної відповіді потрібен новий код/вхід.
- Local confirm quota —1/email/60s, request також1/email/60s; окремі IP budgets.
  Помилковий код теж витрачає cooldown; UI попереджає про це. Знання email може
  дозволити навмисно зайняти cooldown; перед публікацією потрібні provider/edge
  abuse controls. Після cooldown replay окремо перевірено проти справжньої Supabase.

## Видача звичайної сесії та гонки

Після commit web_session, але ДО видачі cookie, accept_identity виконує GET /user
із access JWT. Відмова/timeout/mismatch/cancellation відкликає новий local рядок.
Це необхідне додаткове I/O: затриманий payload, отриманий до reset, не може
обійти і upstream revoke, і final local sweep. Доведено real-local тестом.

У фактичному local gotrue:v2.197.0 знайдено два upstream обмеження:

1. Concurrent verify одного recovery OTP у реальному тесті дав2 успіхи; обидва
   PUT змінили пароль і взаємно відкликали sessions. App-level quota тепер
   відсікає другий confirm ДО provider: одинverify/PUT, один429. Це не обіцянка
   одноразовості прямого Supabase API — він обходить app quota.
2. Pinned token.go перевіряє старий пароль без повторної hash-перевірки під lock
   перед видачею session. Пізня upstream session після reset залишається можливою
   за аналізом source; runtime-відтворення цієї другої гонки не виконано. Master
   уже має LockEncryptedPassword/verifiedHash guard, але це не доказ для local
   чи hosted версії. Перед публічним запуском потрібен виправлений provider і
   повторна перевірка. Не маскувати це epoch у rate_limits або успішним CI.

## UI та середовище

/recovery має дві форми UK/EN у наявному стилі, pending/duplicate guards, помилки,
очищення password/code на виході та no-JS fail-closed. Login recovery-link замінив
старий unavailable dialog. Звичайна email login-форма все ще preview до S03-10;
post-reset login тут доведений справжнім API, не заявлений готовим browser login.

Local email template містить {{ .Token }}; isolated test stack перезапущено зі
збереженням даних. Cloud email template не змінювали. Для хмари потрібна перевірка
можливості template customization/SMTP і реальної доставки. Changelog2026-06-03
обмежує customization на нових Free/default-SMTP проектах; не припускати доступ.
Також лишаються попередні gates: key rotation, cloud0007, hosted smoke/deployment.

## Джерела

- https://supabase.com/docs/guides/auth/auth-email-templates
- https://supabase.com/docs/guides/auth/passwords
- https://github.com/supabase/auth/blob/v2.197.0/internal/api/auth.go
- https://github.com/supabase/auth/blob/v2.197.0/internal/api/token.go
- https://github.com/supabase/auth/blob/master/internal/api/token.go
- https://supabase.com/changelog/46599-changes-to-email-template-customisation-on-free-tier
