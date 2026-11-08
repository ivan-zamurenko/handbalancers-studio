# Полная целевая структура: создавать по карточкам, не все файлы сразу

Це цільова карта roadmap, а не перелік уже готових можливостей. `server/studio`, міграції та public/auth UI вже реалізовані; актуальний стан — у `.workflow/CURRENT.md`, коротка фактична структура — у README.md. `project-map.json` перечисляет целевые пути и задачи, которые их вводят. Каталоги добавляются в задаче первого использования, не сотнями пустых TODO.

```text
handbalancers-studio/
  AGENTS.md                         краткие правила всего репозитория
  README.md                         команды текущего рабочего состояния
  pyproject.toml                    Python package server/studio + test/lint configuration
  uv.lock                           фиксированные Python dependencies
  package.json / package-lock.json  только tooling vanilla JS/browser checks
  .python-version / .node-version
  .env.example                      только имена и пустые значения secrets
  .gitignore / .editorconfig
  .codex/config.toml                рабочая конфигурация coding agent
  .codex/agents/reviewer.toml       независимое read-only review
  .agents/skills/studio-task-delivery/
  .workflow/
    CURRENT.md                      актуальный checkpoint, без многолетнего дневника
    state.json                      статусы карточек и внешних gates
    evidence/Sxx-yy.json             реальные команды, RED/GREEN, результаты
    checkpoints/                    при необходимости снимки передачи контекста
  roadmap/tasks.json                машинный порядок и зависимости
  roadmap/tasks/                    отдельная карточка на каждую ответственность
  docs/                             архитектура, контракты, runbooks, ADR
  references/design/               C1/A1/C3: визуальный reference, не production app
  server/
    studio/
      __init__.py
      main.py                      create_app, registration, lifespan, exception mapper
      settings.py                  typed config, environment validation, secret redaction
      health.py                    live без DB, readiness с проверкой зависимостей
      db.py                        engine/session factory и отдельные role pools
      auth/                        gateway, jwt, session, csrf, limits, OAuth, routes
      accounts/                    profile, preferences, onboarding, coach access
      catalog/                     exercises, immutable revisions, metadata
      programs/                    draft tree, publication, private derivatives
      planning/                    personal plan, assignment, calendar, rules, preview/apply
      training/                    execution snapshot, log, timer, complete, report
      progress/                    read projections по выполненным фактам
      media/                       links, evidence versions, provider access interfaces
      reviews/                     queue, draft, published feedback, private notes
      assessments/                 protocols, criteria, linked sessions, readiness
      billing/                     prices in minor units, Stripe, entitlement, trial
      analysis/                    jobs, inputs, observations, proposals, guarded apply
      coaching/                    только согласованный Pro+ channel
      jobs/                        bounded dispatcher/worker того же монолита
      shared/
        actor.py / authorization.py
        errors.py / http.py / logging.py
        clock.py / identifiers.py
        idempotency.py / audit.py
    templates/
      layouts/{public,member,coach}.html
      shared/{navigation,forms,errors}.html
      auth/{register,verify,login,recovery,complete_profile}.html
      public/{index,plans,onboarding,checkout_pending}.html
      member/{dashboard,programs,program_detail,calendar,workout,result,history,profile}.html
      coach/{desk,clients,client,exercises,exercise_editor,programs,program_editor,
             assignment,review,assessments,planning_rules,permissions}.html
    static/                        runtime assets; css/auth.css для Auth
      css/{tokens,base,components,member,coach}.css
      js/
        api/{client,errors}.js
        components/{form,dialog,theme-control,notice}.js
        state/{session,theme,local-outbox}.js
        features/{auth,public,member,coach,planning,training}/
        i18n/{uk,en}.js
      icons/                       лицензированные SVG, без Apple font files
    alembic/
      env.py
      versions/                    единственный product DDL ledger
    tests/
      conftest.py
      unit/{auth,billing,catalog,planning,training,analysis}/
      contracts/                   реальные HTTP input/output assertions
      integration/                 настоящий local PostgreSQL/Supabase
      security/                    actor spoofing, CSRF, RLS, private output
      support/{database_guard,factories,clock}.py
  supabase/config.toml              local managed services, не второй studio migration ledger
  tests/js/                         Node unit tests pure client behavior
  tests/e2e/                        Playwright с isolated local accounts
  tests/fixtures/                   synthetic data, никогда клиентские ролики
  evals/                            versioned held-out methodology; private evidence вне Git
  tools/                            local stack, checks, roadmap, evidence, benchmarks
  .github/workflows/ci.yml
  Dockerfile / compose.yaml
  tools/previews/handstand/         локальні дизайн-демонстрації, поза runtime static
  docs/runbooks/                    auth setup, restore, deployment, incident handling
```

## Правила роста
Один модуль владеет своими writes. Route не собирает SQL бизнес-операцию из чужих таблиц. Чистое правило можно вызвать из нескольких use cases; HTTP endpoint не вызывается из другого backend endpoint. `shared` содержит только действительно общие механизмы, не бизнес-свалку. Отдельный класс/Protocol нужен на внешней границе либо для полезного contract; generic repository для каждой таблицы не обязателен.

Новый компонент UI = собственная небольшая ES module с init/dispose и явными событиями. Не возвращаться к одному огромному `views.js`. Сначала reuse существующего компонента, затем новый. Event listeners/таймеры удаляются при dispose. Смена темы изменяет tokens/attributes, не вызывает повторный render формы.

## Package и пути
Root `pyproject.toml` описывает package-dir `server`; команды запускаются из root: `uv run uvicorn studio.main:create_app --factory --host 127.0.0.1 --port 8000`. Alembic config явно указывает `server/alembic`, models импортируются через единый registry после создания соответствующего модуля. Не копировать старые абсолютные Mac пути.

Слой wire DTO не принимает серверные actor/role/tier/source owner. Нужны точные Pydantic schemas, forbid лишних security-sensitive полей. SQLAlchemy sync/psycopg3 — принятый инженерный baseline, не совместное async/sync смешение. Внешние async вызовы оборачивать осмысленно без блокировки event loop; маршруты синхронного DB/use-case по умолчанию обычные `def`, внешняя orchestration выделяется и тестируется.
