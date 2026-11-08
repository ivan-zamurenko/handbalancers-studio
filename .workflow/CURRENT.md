# Поточний checkpoint — очищення проєкту, 2026-11-08

За прямим дорученням власника завершено maintenance cleanup перед S03-11.
Видалено підтверджені зайві CSS-правила, старий JS enable loop і два import-only
wrappers. Login template тепер у `server/templates/auth/`; спільний стиль Auth —
`server/static/css/auth.css`. Модулі авторизації/БД/міграції не змінювались.

Демонстрації анімації перенесено з production static у `tools/previews/handstand/`.
Тільки explicit локальний `tools/serve_preview.py` та Playwright harness монтують
`/_previews`; звичайний app повертає 404. Фінальний loading rig збережено.
README та LOCAL_PREVIEW оновлено. Попередні 617 рядків checkpoint без змін
збережено в [архіві](history/2026-11-08-through-S03-10.md); шляхи у ньому від кореня.

Перевірки й review — у `.workflow/evidence/maintenance-cleanup.json`.
GREEN: 85 browser, 41 JS, 231 Python runtime, 68 tooling (+25 subtests);
Ruff/format/Mypy. Reviewer clear. Staged tree roadmap validator пройшов.
Коміт і push виконуються після цього checkpoint; SHA буде у звіті власнику.

## Авторизація та наступний крок

S03-10 завершено: `f3d4e03`, pushed. Форми реєстрації/коду/password login
підключені; Google лишається, Apple відсутній. Докладні докази:
`.workflow/evidence/S03-10.json`. Наступна картка — S03-11, повний локальний Auth E2E.
Hosted OTP/recovery, key rotation, cloud 0007 та provider gates не закривалися
UI-тестами або поточним cleanup; див. попередній checkpoint і evidence.

У робочому дереві залишаються сторонні видалення docs та локальні editor/skill
файли. Вони не включаються в cleanup. Повний file validator у цьому дереві
має попередні missing_document; graph і staged tree перевіряються окремо.
