# Skills проєкту

У репозиторії зберігаються три перевірені за призначенням набори:

| Skill | Призначення |
|---|---|
| `.agents/skills/studio-task-delivery/` | Проєктний процес: картка, test-first, review та evidence |
| `.agents/skills/supabase/` | Документація й правила роботи з Supabase Auth/DB/CLI |
| `.agents/skills/supabase-postgres-best-practices/` | SQL, schema, RLS та PostgreSQL performance |

Два Supabase skills — раніше встановлений snapshot з
[supabase/agent-skills](https://github.com/supabase/agent-skills), не нова установка
чи оновлення. Файли збережено без зміни upstream інструкцій. Походження й hashes
інсталятора — `skills-lock.json`; SHA-256 збережених локальних файлів — у
`.workflow/evidence/workspace-residue-cleanup.json`.
[MIT license](vendor/supabase-agent-skills-LICENSE.txt) збережена поруч із документами.

Ці skills не є runtime-залежностями й не запускають команди самостійно.
Читати лише релевантний skill і потрібні references. Інструкції власника,
AGENTS.md та погоджений стек мають пріоритет над рекомендаціями сторонніх skills;
наприклад, продукт використовує Alembic для власних схем, а не паралельну
історію Supabase CLI migrations. Snapshot не оновлювати без окремого review.

`.claude/skills/` містить лише локальні symlink aliases на `.agents/skills/`
і виключений із Git. `.vscode/` — персональні налаштування та MCP-підключення,
також поза Git. Короткий Copilot adapter — `.github/copilot-instructions.md`;
він посилається на спільний контракт замість дублювання правил.

Стан і дозволи визначаються поточним дорученням та checkpoint, не прикладами
у сторонніх довідниках. Skills і зелені тести самі по собі не гарантують безпеку.
