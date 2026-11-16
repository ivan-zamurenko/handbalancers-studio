# Поточний checkpoint — S03-11 auth local e2e, 2026-11-16

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

## Наступний крок

S04-01 `oauth_attempt` — Google OAuth через Supabase PKCE (`tools/roadmap.py next`).
