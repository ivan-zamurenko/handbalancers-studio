# S03-10c — Анімоване око в полі пароля

Явний запит: перемикач справа всередині поля; око відкривається при показі
пароля і закривається при маскуванні. SVG/CSS без нових залежностей.
UK/EN accessible name, aria-pressed, keyboard,44px target,reduced motion.
Не змінювати пароль і не зберігати його; pagehide зберігає SVG та скидає стан.
Тести: npx playwright test tests/e2e/login-form.spec.js tests/e2e/oauth-ui.spec.js.
Commit: feat(ui): [S03-10c] animate inline password eye
