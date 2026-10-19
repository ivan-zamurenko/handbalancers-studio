# S03-10a — Форма входу для перегляду

Явний запит власника 2026-10-19: додати форму логіну.
Незалежний UI зріз S03-10, без завершення auth/session/CSRF залежностей.
GET /login: email, пароль, показ/приховування, пояснення відновлення доступу,
реєстрації та поточного стану. UK/EN, light/dark, 390/1440, клавіатура.
Submit заблоковано також без JS; credentials не надсилаються і не пишуться
у localStorage/sessionStorage. При pagehide пароль очищується і приховується.
Тести: npx playwright test tests/e2e/login-form.spec.js.
Commit: feat(ui): [S03-10a] login form preview
