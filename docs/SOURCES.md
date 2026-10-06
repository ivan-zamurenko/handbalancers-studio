# Источники и границы применимости

Дата проверки: 6 октября 2026. Продуктовые правила взяты из диалога и переданных handoff; технические defaults — наши проектные решения, не скрытые требования документации. Ссылки ниже — первичные внешние источники для проверяемых API/инструментов. Мы не копируем их тексты целиком. Версии и account access ещё раз проверить при установке.

## S-MODEL — GPT-6 Astra model

https://developers.openai.com/api/docs/models/gpt-6-astra

Model identifier/reasoning values; direct video input not supported. Not a claim of account access.

## S-MODELGUIDE — Using GPT-6

https://developers.openai.com/api/docs/guides/latest-model

Responses/tooling and model parameter compatibility.

## S-CONFIG — Codex configuration reference

https://learn.chatgpt.com/docs/config-file/config-reference

model, effort, sandbox, approvals and subagent config fields.

## S-AGENTS — AGENTS.md instructions

https://learn.chatgpt.com/docs/agent-configuration/agents-md

Repository instructions loading. Our task/checkpoint rules are project-specific.

## S-SKILLBLOG — Rethinking skills and prompts for GPT-6 Astra

https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra

Narrow triggers, progressive context and avoiding irrelevant instruction bloat.

## S-SKILLS — Agent skills

https://learn.chatgpt.com/docs/build-skills

Repository skill location and skill mechanics.

## S-SUBAGENTS — Subagents

https://learn.chatgpt.com/docs/agent-configuration/subagents

Scoped delegation and agent role configuration.

## S-WORKTREE — Git worktrees

https://learn.chatgpt.com/docs/environments/git-worktrees

Separate working trees; our DB/port isolation rule supplements this.

## S-PKCE — Supabase PKCE

https://supabase.com/docs/guides/auth/sessions/pkce-flow

Code/verifier exchange and browser flow constraints.

## S-AUTHSSR — Supabase server-side advanced guide

https://supabase.com/docs/guides/auth/server-side/advanced-guide

Token refresh/trusted auth state considerations.

## S-LINKING — Supabase identity linking

https://supabase.com/docs/guides/auth/auth-identity-linking

Provider-managed verified identity linking.

## S-APPLE — Supabase Apple login

https://supabase.com/docs/guides/auth/social-login/auth-apple

Apple web configuration, secret rotation, profile attributes.

## S-PASSWORD — Supabase password auth

https://supabase.com/docs/guides/auth/passwords

Managed email/password flow.

## S-SUPABASELOCAL — Local development database migrations

https://supabase.com/docs/guides/local-development/database-migrations

Local services and schema workflow; choice of Alembic for product is our architecture.

## S-RLS — PostgreSQL row security

https://www.postgresql.org/docs/current/ddl-rowsecurity.html

RLS scope and owner/BYPASSRLS exceptions.

## S-ORMVERSION — SQLAlchemy version counters

https://docs.sqlalchemy.org/en/20/orm/versioning.html

Optimistic version checks and bulk-operation limitations.

## S-ALEMBIC — Alembic autogenerate

https://alembic.sqlalchemy.org/en/latest/autogenerate.html

Generated revisions need review; detection limits.

## S-FASTAPI — FastAPI testing

https://fastapi.tiangolo.com/tutorial/testing/

Application HTTP testing pattern.

## S-PW — Playwright best practices

https://playwright.dev/docs/best-practices

Isolated user-visible tests/locators; project snapshot matrix is our choice.

## S-PYTEST — pytest fixtures

https://docs.pytest.org/en/stable/how-to/fixtures.html

Fixture scope/teardown; our red-green policy follows user mandate.

## S-STRIPE — Stripe webhooks

https://docs.stripe.com/webhooks

Signature handling, duplicates/retries/out-of-order delivery.

## S-TRIAL — Stripe subscription trials

https://docs.stripe.com/billing/subscriptions/trials

Trial mechanics; 7-day/tier rules supplied by owner.
