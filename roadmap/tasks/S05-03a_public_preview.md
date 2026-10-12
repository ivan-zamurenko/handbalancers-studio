# S05-03a — Публічний лендінг для локального перегляду

Підзадача S05-03, виділена за дорученням власника 2026-10-12 працювати до
запущеного лендінгу. Залежить від S02-05 і завершеного S03-03. Решта auth,
профіль, анкета та інтеграція S05-03 з повним onboarding залишаються відкритими.

Обсяг: public index/plans templates, plans.js, public CSS, public routes/copy,
main static/router registry, підключення theme selector, browser acceptance.
Без authenticated/paid API, зовнішніх провайдерів, deployment чи fake даних.

Вимоги S05-03: EUR1999/4999/17999/29999 на місяць; trial7днів з карткою та
автосписанням лише Essential/Plus; явний вибір переживає reload, Plus fallback;
немає вигаданих відгуків або працюючого AI. Додатково: UK/EN, light/dark,
390/1440, робочі anchor links, keyboard, missing storage, no-JS presentation.
Недоступні реєстрація/оплата позначені перед продовженням, жодних fake success.

Джерела: docs/decisions.md, docs/contracts.md (HEAD через user deletions),
references/design/preview/assets/design-tokens.json і selected.css;
затверджені public тексти з references/MODEL_HANDOFF_HISTORICAL.md секції6/7
як прямо вказано S05-03. Старий код не читати/копіювати.

Перевірка: `npx playwright test tests/e2e/s05-03-public-pages.spec.js`.
Default Chromium без неіснуючого named project. Спершу RED, потім GREEN.
Review, окремий commit `feat(onboarding): [S05-03a] public landing preview`, push.
Після GREEN запустити локальний dev server127.0.0.1:8000 та перевірити HTTP/browser.
