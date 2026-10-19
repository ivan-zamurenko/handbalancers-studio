# S04-03a — OAuth у формі входу

Підключити Google/Apple до готового server start endpoint. Показувати тільки
увімкнених провайдерів. Pending блокує повтор, failure відновлює кнопку;
callback cancellation/error пояснюється без provider details.
Сесія показує стан входу і вихід через CSRF; гість не бачить logout.
UK/EN,390/1440,light/dark; email/password залишається явно preview.
Тести: npx playwright test tests/e2e/login-form.spec.js tests/e2e/oauth-ui.spec.js.
Commit: feat(ui): [S04-03a] connect OAuth login controls
