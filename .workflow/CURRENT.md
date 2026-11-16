# Поточний checkpoint — S04-01 oauth attempt, 2026-11-16

S04-01 виконано локально (IMPLEMENTED_LOCAL). Поведінку вже реалізувала S04-01a,
тому RED поведінки немає (чесно записано); додано тести картки
`server/tests/security/accounts/test_oauth_attempt.py`: PKCE verifier на кожну
спробу, allowlist return_to і провайдерів, паралельні старти без змішування.
GREEN 15; regression security+oauth+contracts 209; 6 мутацій зловлено; review —
2 слабкі асерти виправлено. Докази: `.workflow/evidence/S04-01.json`.

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

S04-02 `oauth_callback` — обмін OAuth code і відновлення шляху користувача (`tools/roadmap.py next`).
