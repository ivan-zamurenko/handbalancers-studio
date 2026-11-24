# S14-18 — Добирати рекомендації лише з каталогу

**Статус документа:** погоджена картка; фактичне виконання тільки у `.workflow/state.json`.

Перевірений набір вправ/уточнень для майбутньої пропозиції.

| Поле | Значення |
|---|---|
| Основний відповідальний | AI Engineer |
| Складність | M |
| Залежить від | S14-17, S06-06, S11-01 |
| Локальні gates | Немає; реальні дані/провайдери — за чинними owner-gates |

## Контекст і межі

- `docs/ai-coaching.md`
- `docs/contracts.md`
- `docs/owner-gates.md`

Входи: CoachExplanation, approved catalog і structured profile constraints. Published planning_rule_set from S11-01; do not create a second rules store.

Виходи: Перевірений набір вправ/уточнень для майбутньої пропозиції.

## Файли відповідальності

- `server/studio/analysis/recommendations.py`
- `server/tests/integration/analysis/test_catalog_recommendations.py`

Це майбутні шляхи, не твердження про наявність реалізації. Міграція створюється лише перед першою командою, яка її використовує; номер береться від фактичного Alembic head. Інтегратор одноосібно редагує міграції/state. Чужі модулі — тільки через погоджений контракт.

## Перевірювані сценарії

| Сценарій | Очікуваний результат |
|---|---|
| `allowlisted_versions` | Лише published доступні exercise versions; невідомі/чужі/private/revoked IDs відхилено. |
| `constraints_and_load` | Враховано рівень, ціль, equipment, prerequisites і затверджені правила навантаження; невідомі норми не генеруються. |
| `explain_selection` | Кожна вправа пов’язана зі спостереженням/метою/джерелом; гіпотеза явно непідтверджена. |
| `no_plan_write` | Генерація рекомендацій не записує програму й не створює нову вправу в каталозі. |

## HTTP / компонентний контракт

Recommendation[]: exercise_version_id, purpose, evidence/source refs, constraints, assessment need.

## Дані

Версійні recommendations із FK до published catalog і analysis run; наступна revision.

## Виконання та Definition of Done

1. Перевірити prerequisites, фактичний scope і поточні API/DB contracts. Для коду — тест сценарію, спостережуваний RED з правильної причини, мінімальна реалізація, GREEN. Для документації/дослідження — validator або reproducible evaluation, без фіктивних тестів.
2. Виконати вузьку перевірку нижче, потім affected-module suite. DB/RLS/concurrency — на реальному ізольованому PostgreSQL. UI — особистий перегляд актуальних screenshots за AGENTS.md; навчальні приклади лише synthetic.
3. Перевірити owner/permission/entitlement, обмеження ресурсів, приватність і відмови. Немає реального стенда/дозволу — env_blocked у evidence; mock не підтверджує provider quality.
4. Незалежний read-only review; оновити CURRENT/state/evidence, один GREEN commit у чинній task/execution-v4. Push лише підтвердженому origin; без merge/deploy/hosted migrations.

Команда після створення відповідного тесту/harness:

```sh
uv run pytest server/tests/integration/analysis/test_catalog_recommendations.py -q
```

Commit subject:

```text
feat(analysis): [S14-18] catalog recommendations
```

Докази: `.workflow/evidence/S14-18.json`; фактичний SHA повідомляється після commit.

Навчання: обрати один невеликий фрагмент із [навчальної послідовності](../../docs/learning/README.md). Користувач пише власну ділянку; агент не перезаписує її й перевіряє перед інтеграцією.
