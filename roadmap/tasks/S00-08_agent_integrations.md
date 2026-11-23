# S00-08 — Superpowers + Firecrawl

Власник доручив встановити та почати використовувати ці GitHub-проєкти.
Scope: project-local Codex skills, Firecrawl CLI/MCP, документація й перевірка.

- Codex має реально виявляти15 Superpowers і13 Firecrawl skills.
- CLI та MCP мають виконати реальні запити публічної документації.
- Авторизація використовує локальне сховище CLI; секретів у Git/чаті немає.
- Helper відхиляє credential для іншого API origin і header injection.
- Глобальні/вебплагіни, продуктова логіка, БД, deploy не змінюються.

Validator: Codex skills/list + mcp get + authenticated RPC + CLI scrape.
RED→GREEN: tools/tests/test_firecrawl_headers.py.
Commit: chore(tooling): [S00-08] connect Superpowers and Firecrawl.
