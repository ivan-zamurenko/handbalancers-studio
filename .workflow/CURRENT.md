# Поточний checkpoint — S05-01 анкета у профілі, 2026-11-18

Профіль = форма з анкетою (цілі, рівень, 1–3 дні, час, 30/45/60/90 хв, рік народження/зріст/вага
необов’язково). Обмеження однакові в UI/API/БД; міграція 0010; setup_required → одноразовий
перехід у профіль. Хмара: 0010 застосовано власником 2026-11-18, незалежна read-only перевірка таблиці/RLS пройшла. Докази: `.workflow/evidence/S05-01.json`.

## Хмарна міграція 0010 завершена — 2026-11-18

Власник дозволив застосування та виконав підготовлену команду з прихованим
паролем postgres. Результат: Applied migration upgrade to Alembic 0010;
ownership and RLS verified. Baseline 0006 незмінний; новий approved target 0010.
Незалежна read-only перевірка через runtime-з’єднання: таблиця анкети існує,
власник postgres, RLS увімкнено, три own-row політики, anon/authenticated/
studio_auth_runtime/studio_worker без доступу, без user context записи не видно.
Локально: 42 DB тести пройшли (0009→0010, повторний запуск, збереження даних,
відмова при drift політик/дозволів, API анкети), Ruff і mypy пройшли.
Хмарний gate 0010 закрито. Повний ручний save через браузер у хмару ще не перевірений.
Докази: `.workflow/evidence/cloud-0010-2026-11-18.json`.
Наступний roadmap-крок залишається S05-02.

## Анімації та мобільний UX закомічено й запушено — 2026-11-18

Анімації вже підключені: member/profile.html → profile.js → playSaveFeedback,
після відповіді на submit. Runtime — SVG/JS/CSS у server/static, GIF/відео не потрібні.
Погоджені зміни анімацій, мобільної форми й меню перевірено разом:
56 JS тестів + 56 браузерних сценаріїв пройшли, read-only review без блокерів.
Усі 323 файли private-evidence ігноруються, відстежуваних приватних файлів немає.
Коміт 6e89eb2 запушено в origin/task/execution-v4 явним списком файлів.
Ручне хмарне збереження ще не перевірене; міграцію 0010 застосовано (див. вище).
Докази: `.workflow/evidence/save-feedback-delivery-2026-11-18.json`.

## Погоджені анімації збереження — 2026-11-18

Залишено поточні реалізовані варіанти:
- Успіх: виштовхування на опорному плечі, утримання 1 с,
  контурний водоворот у зелене коло з білою галкою та «Збережено» (v3).
- Помилка: втрата балансу, водоворот ще під час падіння до приземлення,
  червоне коло з білим хрестиком та «Виникла помилка» (v4).

Власник погодив обидва варіанти й доручив прибрати непотрібні.
Погоджені записи: `private-evidence/save-feedback-approved/success.mp4`
і `private-evidence/save-feedback-approved/error.mp4` (синтетичні API, поза Git).
Видалено застарілі/дубльовані медіафайли, старі capture-скрипти,
окрему сторінку tools/previews/save-feedback та її невикористовуваний previewPose.
Мобільні UI-знімки й історію RED/GREEN збережено; шляхи в evidence актуалізовано.
Докази руху: `.workflow/evidence/save-motion-2026-11-18-v3.json`,
`.workflow/evidence/save-motion-2026-11-18-v4.json`.
Анімації лише після відповіді на відправку форми. Хмарний gate 0010 закрито (див. вище).
Очищення не змінює погоджені рухи; 5/5 браузерних перевірок форми пройшли.
Докази: `.workflow/evidence/save-feedback-cleanup-2026-11-18.json`. Commit/push не виконували.

## UX-виправлення за дорученням власника — 2026-11-18

Локально перероблено падіння (контакт ноги → згинання коліна → відрив кисті → бік),
анімація лише після відповіді сервера, секундний hold успіху, пропуск/reduced-motion,
повернення фокусу. На телефоні бургер-меню, покрокове перше заповнення та акордеон
редагування; великі radio-варіанти, нижні кнопки, числові поля по одному в ряд.
Виправлено конфлікт inert при відкритті меню під час запиту.
Перевірено 56 браузерних сценаріїв (55/56 у загальному запуску, після виправлення
гонки тесту logout — 8/8 його suite), 50 JS тестів. Знімки 320/390/1440, обидві теми,
UI-знімки — в ігнорованій `private-evidence/save-mobile-2026-11-18/`.
Старі записи анімацій із цієї папки видалено після погодження фінальних варіантів. Не перевірено фізичний телефон/Safari
та hosted збереження з 0010. Докази: `.workflow/evidence/save-mobile-2026-11-18.json`.
Наявні на початку незакомічені зміни меню збережено й допрацьовано; коміту/push
цього доручення не робили. Наступний roadmap-крок залишається S05-02.

## Попередньо — макет кабінету (профіль + прогрес), 2026-11-16

Власник визначив зміст профілю й метрики прогресу (`docs/decisions.md`,
«Профіль і прогрес»), включно з heat map регулярності як у GitHub. Зроблено
синтетичний макет у стилі C1: `tools/previews/cabinet/{profile,progress}.html`
(390/1440, обидві теми, без помилок/переповнення). Чекає погодження власника;
логіку не реалізовано. Сервер 8000 перезапущено на поточному коді (власник
дозволив); /api/me у хмарі = 503 (немає DATABASE_URL і міграцій 0008/0009).

## Хмарна міграція 0007–0009 (дозвіл власника 2026-11-17)

`tools/migrate_cloud.py`: APPROVED_CLOUD_REVISION=0009 (adoption лишається 0006);
тести: прийнята база 0006 → 0009 з незмінними даними; DB suites зелені.
Web-логін тепер відхиляється, якщо ширший за studio_web (UnsafeWebRole).
SQL для логіна: `supabase/web-login.sql`; інструкція: `.workflow/REGISTRATION_BASELINE.md`.
Статус: застосовано власником; хмара на 0009, studio_web_app працює, /api/me = 401 без входу (раніше 503).

## Наступний крок

Після погодження макета: розкласти профіль/прогрес на картки roadmap
(вік/зріст/вага — G_PRIVACY; метрики залежать від S08/S09 тренувальних фактів).

## Попередньо — S04-06 profile & preferences

S04-06 виконано локально: сторінка /profile (ім’я, прізвище, мова, тема),
API /api/me/profile і /api/me/preferences (ревізія, 409 при конфлікті) від імені
studio_web під RLS; міграція 0009 (studio.user_preferences). Тема акаунта
зберігається під studio:account:<id>:theme і очищається при виході.
Review знайшов 2 гонки теми на клієнті — виправлено й перевірено в браузері.
У хмарі: DATABASE_URL не налаштовано, 0008/0009 не застосовано → /api/me = 503.
Докази: `.workflow/evidence/S04-06.json`.

## Попередньо — S04-05 coach bootstrap

S04-05 виконано локально: роль coach видає лише власник CLI
`python -m studio.accounts.cli grant-coach|revoke-coach <auth_user_id> --actor <ім'я>`
(операторський DB-доступ, не email), з аудитом у новій таблиці
`studio_private.audit_events` (міграція 0008, RLS, без грантів runtime-ролям).
RED 4→GREEN 4; check_migrations усі набори зелені; review clear.
У хмарній БД 0008 НЕ застосовано — потрібен дозвіл власника.
Докази: `.workflow/evidence/S04-05.json`.

## Попередньо — S04-04 identity linking

S04-04 виконано локально: профіль = auth UUID, без злиття за email. 4 тести
(`server/tests/security/accounts/test_identity_linking.py`), 2 ключові мутації
зловлено, regression 127. Код не змінювався. Докази: `.workflow/evidence/S04-04.json`.
Власник 2026-11-16: лише необхідні й критичні тести, без надмірності.

## Попередньо — Apple видалено, S04-03 skipped

За рішенням власника Apple-вхід видалено з коду (allowlist лише google, налаштування
oauth_apple_enabled прибрано, docs оновлено); S04-03 — skipped, S04-04 тепер залежить
від S04-02. CHECK у БД (0004) ще допускає 'apple' — застосунок не записує.
RED→GREEN; checks.py exit 0; DB suites 202. Докази: `.workflow/evidence/S04-03.json`.
Причина й правила для агентів: `docs/adr/apple-sign-in-removed.md` (посилання також в AGENTS.md).

## Попередньо — S04-02 oauth callback

S04-02 виконано локально (IMPLEMENTED_LOCAL). Поведінка callback уже була з S04-01a;
додано HTTP-тести `server/tests/security/accounts/test_oauth_callback.py`
(DB-suite замість contracts/, бо contracts у CI без БД): replay, чужий браузер,
скасування з повторною спробою, профіль один раз, redirect лише на дозволений шлях,
code не в серверних логах. 7 GREEN; DB suites 201; 6 мутацій зловлено; review —
перевірку логів посилено. Докази: `.workflow/evidence/S04-02.json`.

## Попередньо — S04-01 oauth attempt

S04-01 виконано локально (IMPLEMENTED_LOCAL). Поведінку вже реалізувала S04-01a,
тому RED поведінки немає (чесно записано); додано тести картки
`server/tests/security/accounts/test_oauth_attempt.py`: PKCE verifier на кожну
спробу, allowlist return_to і провайдерів, паралельні старти без змішування.
GREEN 15; regression security+oauth+contracts 209; 6 мутацій зловлено; review —
2 слабкі асерти виправлено. Докази: `.workflow/evidence/S04-01.json`.

## CI-ремонт (2026-11-16)

CI був червоний з 4b4c4b4: (1) pip-audit — CVE-2026-126360 у opentelemetry-api
1.45.1 → оновлено до 1.45.2 у uv.lock; (2) з 7544ace DB-job — тест відновлення
шукав лист за українською темою; тепер тема береться з supabase/config.toml.
Також `server/tests/security/accounts` (S04-01) додано в DB_SUITES CI.
Локально: baseline checks.py зелений; DB suites 179 passed; tools/tests 68.

## Попередньо — S03-11 auth local e2e

S03-11 виконано локально (IMPLEMENTED_LOCAL, live_verified=false).
Наскрізний gate на реальному local Supabase test stack без моків:
register → код лише з loopback Mailpit (лист видаляється в catcher) →
verify → session → logout (CSRF) → login. Профіль пов'язаний з реальним
managed `auth.users` (validated FK), повторний login не створює профіль,
після logout стара cookie дає 401, а upstream refresh token відхиляється.

Нове: `tools/local_auth_fixture.py`, `server/tests/integration/auth/test_auth_local_e2e.py`.
RED: ImportError відсутньої фікстури. GREEN: 4 passed; regression
`server/tests/integration/auth`: 100 passed; мутаційна перевірка ловить
невидалений лист і відсутній auth user. Review — clear.
Докази: `.workflow/evidence/S03-11.json`.

Запуск: Colima `studio-s01`, `DOCKER_HOST=unix://$HOME/.colima/studio-s01/docker.sock
DOCKER_CONTEXT=default .venv/bin/python -m tools.local_stack test .venv/bin/python -m pytest …`.

Не підтверджено: hosted email/SMTP, Google OAuth live, браузерний шлях цього gate.
Hosted OTP/recovery, key rotation, cloud 0007 та provider gates лишаються відкритими.
Попередній checkpoint (мобільна навігація, `9ff4f3d`): `history/2026-11-08-mobile-navigation.md`.

## Live-перевірка hosted dev (2026-11-16)

Google-вхід працює (з боку власника). Лист на новий аліас доставлено вбудованим
SMTP Supabase, але hosted-шаблон надсилає посилання, а не 6-значний код —
підтвердження на hosted неможливе, доки шаблон не змінено (на поточному плані
редагування недоступне). Для наявного email лист не надсилається навмисно;
на сторінці коду додано нейтральну підказку.
Потім: домен handbalancers.com (Cloudflare), Resend SMTP `no-reply@mail.handbalancers.com`,
англійські шаблони в дизайні застосунку, OTP 6 цифр. Власник підтвердив: лист
реєстрації й скидання пароля у «Вхідних», обидва сценарії пройдені. DMARC p=none опубліковано. Докази:
`.workflow/evidence/live-auth-check-2026-11-16.json`. G_SMTP/G_AUTH_PROVIDERS — pending.

## Наступний крок

S05-01 `onboarding_model` — Сохранить анкету без медицинского scoring (`tools/roadmap.py next`).
