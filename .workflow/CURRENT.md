# Поточний checkpoint — Apple видалено, S04-03 skipped, 2026-11-16

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

S04-04 `identity_linking` — linking і конфлікти identities (`tools/roadmap.py next`).
