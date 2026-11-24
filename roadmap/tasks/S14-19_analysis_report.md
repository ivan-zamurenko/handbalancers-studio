# S14-19 — Показати версійний звіт і скелет у Studio

**Статус документа:** погоджена картка; фактичне виконання тільки у `.workflow/state.json`.

Вбудований звіт із Canvas/SVG overlay; новий frontend runtime не потрібен.

| Поле | Значення |
|---|---|
| Основний відповідальний | Frontend |
| Складність | L |
| Залежить від | S14-18, S09-04, S10-13, S10-14 |
| Локальні gates | Немає; реальні дані/провайдери — за чинними owner-gates |

## Контекст і межі

- `docs/ai-coaching.md`
- `docs/contracts.md`
- `docs/owner-gates.md`

Входи: Analysis run, recommendation set, authorized media і current Studio shell.

Виходи: Вбудований звіт із Canvas/SVG overlay; новий frontend runtime не потрібен.

## Файли відповідальності

- `server/studio/analysis/reports.py`
- `server/studio/analysis/routes.py`
- `server/studio/analysis/service.py`
- `server/studio/analysis/models.py`
- `server/studio/jobs/analysis_worker.py`
- `server/tests/integration/analysis/test_report_persistence.py`
- `server/templates/member/analysis.html`
- `server/templates/coach/analysis_detail.html`
- `server/static/js/features/analysis/status.js`
- `tests/e2e/analysis_report.spec.js`

Це майбутні шляхи, не твердження про наявність реалізації. Міграція створюється лише перед першою командою, яка її використовує; номер береться від фактичного Alembic head. Інтегратор одноосібно редагує міграції/state. Чужі модулі — тільки через погоджений контракт.

## Перевірювані сценарії

| Сценарій | Очікуваний результат |
|---|---|
| `owner_report` | Власний report no-store; чужий приховано; report-only проходить permissions/quality gates і не викликає apply. |
| `overlay_sync` | Скелет відповідає часу, rotation/crop/resize; pause/seek працює; missing intervals не домальовуються. |
| `immutable_report` | Заміна відео/методики не підміняє старий звіт; є обмеження, джерела й точні evidence timestamps. |
| `visual_states` | Переглянуті 1440/390/320, light/dark, UA/EN, keyboard, queued/needs_input/failed/succeeded та видалене evidence. |
| `persist_owner_bound_results` | Реальна test DB перевіряє typed metrics/quality/report owner/run FK, RLS для двох користувачів, immutable versions, atomic rollback і duplicate publication. |
| `pipeline_and_revocation` | Оркестрація pose→quality→metrics→retrieval→coach→recommendations завершує один versioned report; низька якість зупиняє downstream; revoke/delete/stale lease забороняє publish. |

## HTTP / компонентний контракт

Owner-only POST /api/session-exercises/{id}/analyses; GET /api/analyses/{id} status/result; scoped artifact access. Existing status DTO перевикористати.

## Дані

Адитивні typed metric/quality rows і immutable report versions з owner/run/criterion/source refs та індексами; наступна фактична revision, реальні DB/RLS/rollback/concurrency тести. Без нових training facts.

## Виконання та Definition of Done

1. Перевірити prerequisites, фактичний scope і поточні API/DB contracts. Для коду — тест сценарію, спостережуваний RED з правильної причини, мінімальна реалізація, GREEN. Для документації/дослідження — validator або reproducible evaluation, без фіктивних тестів.
2. Виконати вузьку перевірку нижче, потім affected-module suite. DB/RLS/concurrency — на реальному ізольованому PostgreSQL. UI — особистий перегляд актуальних screenshots за AGENTS.md; навчальні приклади лише synthetic.
3. Перевірити owner/permission/entitlement, обмеження ресурсів, приватність і відмови. Немає реального стенда/дозволу — env_blocked у evidence; mock не підтверджує provider quality.
4. Незалежний read-only review; оновити CURRENT/state/evidence, один GREEN commit у чинній task/execution-v4. Push лише підтвердженому origin; без merge/deploy/hosted migrations.

Команда після створення відповідного тесту/harness:

```sh
uv run pytest server/tests/integration/analysis/test_report_persistence.py -q && npx playwright test tests/e2e/analysis_report.spec.js
```

Commit subject:

```text
feat(analysis): [S14-19] analysis report
```

Докази: `.workflow/evidence/S14-19.json`; фактичний SHA повідомляється після commit.

Навчання: обрати один невеликий фрагмент із [навчальної послідовності](../../docs/learning/README.md). Користувач пише власну ділянку; агент не перезаписує її й перевіряє перед інтеграцією.

## Уточнення

Один primary owner Frontend інтегрує звіт; DB/migrations перевіряє інтегратор, reviewer read-only. S14-09 пізніше доповнює цей самий UI авторством/before-after адаптації, не створює другий звіт.
