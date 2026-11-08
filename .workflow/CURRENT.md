# Поточний checkpoint — порядок у Git, 2026-11-08

За прямим дорученням власника розібрано всі 70 залишкових змін робочого дерева.
Відновлено 20 потрібних документів: їх видалення ламало посилання roadmap.
Оновлено застарілі вказівки про Apple, нову папку/гілку, структуру та команди.
Видалено старий пакет Copilot (5 файлів) і тимчасові задачі VS Code;
замість дубльованих інструкцій — короткий `.github/copilot-instructions.md`.
Локальна резервна копія видаленого — у виключеному `private-evidence/`.

40 файлів раніше встановлених Supabase skills та `skills-lock.json` збережено
у version control; походження, MIT license та межі застосування описано в
`docs/skills-policy.md`. Персональні `.vscode/`, skill aliases `.claude/skills/`
та матеріали дописів `private-evidence/` залишаються локальними й ignored.

Перевірено в реальному робочому дереві: roadmap valid (142 картки, 0 помилок),
16 тестів roadmap, JSON/skill metadata, нові локальні посилання, ignore scope,
контрольні суми 40 skill-файлів і перевірка credential patterns.
Незалежний review виявив неточність DB-команд; виправлено README/toolchain:
prepare перед start; `--fresh` лише для порожніх продуктових схем.
Runtime, БД і залежності не змінено; їхні тести повторно не запускалися.
Докази — `.workflow/evidence/workspace-residue-cleanup.json`.
Commit/push — після фінальної перевірки; фактичний SHA у звіті власнику.

## Попередній результат та наступний крок

Попереднє очищення runtime завершено й pushed: `c359849`.
Його перевірки (85 browser, 41 JS, 231 Python, 68 tooling +25 subtests)
записані в `.workflow/evidence/maintenance-cleanup.json`; це попередній запуск.
Історичний checkpoint — [архів](history/2026-11-08-through-S03-10.md).

S03-10 завершено: `f3d4e03`, pushed. Google та email/password лишаються,
Apple виключено власником. Наступна картка — S03-11, повний локальний Auth E2E.
Hosted OTP/recovery, key rotation, cloud 0007 та provider gates не закриті
поточним cleanup; див. архів checkpoint та evidence відповідних перевірок.
