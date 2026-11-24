# S14-14 — Обчислювати явні метрики біомеханіки

**Статус документа:** погоджена картка; фактичне виконання тільки у `.workflow/state.json`.

Відтворювані метрики доступних суглобів, лінії та руху в часі.

| Поле | Значення |
|---|---|
| Основний відповідальний | Biomechanics |
| Складність | M |
| Залежить від | S14-13 |
| Локальні gates | Немає; реальні дані/провайдери — за чинними owner-gates |

## Контекст і межі

- `docs/ai-coaching.md`
- `docs/contracts.md`
- `docs/owner-gates.md`

Входи: Перевірені pose intervals і методика.

Виходи: Відтворювані метрики доступних суглобів, лінії та руху в часі.

## Файли відповідальності

- `server/studio/analysis/biomechanics.py`
- `server/tests/unit/analysis/test_biomechanics_metrics.py`

Це майбутні шляхи, не твердження про наявність реалізації. Міграція створюється лише перед першою командою, яка її використовує; номер береться від фактичного Alembic head. Інтегратор одноосібно редагує міграції/state. Чужі модулі — тільки через погоджений контракт.

## Перевірювані сценарії

| Сценарій | Очікуваний результат |
|---|---|
| `analytic_geometry` | Відомі геометричні fixtures перевіряють кути, сегменти, units і нульову довжину вектора. |
| `aspect_ratio` | Різні width/height, rotation/crop transform не спотворюють кути нормованих координат. |
| `temporal_metrics` | Стабільність/тривалість враховують реальні timestamps і gaps, не frame_count/fps assumption. |
| `measurement_limits` | 2D projected angle не видається за точний анатомічний 3D кут; missing/noisy дані не стають результатом. |
| `model_cannot_override` | MetricResult зберігає значення/одиниці/інтервал/версію/якість незалежно від LLM. |

## HTTP / компонентний контракт

calculate_metrics(PoseSequence, QualityAssessment, MethodVersion) -> MetricResult[]; чисті Python-функції.

## Дані

Немає DDL. MetricResult — чистий typed DTO; owner-bound metric rows, FK/indexes/provenance реалізуються й DB-тестуються в S14-19.

## Виконання та Definition of Done

1. Перевірити prerequisites, фактичний scope і поточні API/DB contracts. Для коду — тест сценарію, спостережуваний RED з правильної причини, мінімальна реалізація, GREEN. Для документації/дослідження — validator або reproducible evaluation, без фіктивних тестів.
2. Виконати вузьку перевірку нижче, потім affected-module suite. DB/RLS/concurrency — на реальному ізольованому PostgreSQL. UI — особистий перегляд актуальних screenshots за AGENTS.md; навчальні приклади лише synthetic.
3. Перевірити owner/permission/entitlement, обмеження ресурсів, приватність і відмови. Немає реального стенда/дозволу — env_blocked у evidence; mock не підтверджує provider quality.
4. Незалежний read-only review; оновити CURRENT/state/evidence, один GREEN commit у чинній task/execution-v4. Push лише підтвердженому origin; без merge/deploy/hosted migrations.

Команда після створення відповідного тесту/harness:

```sh
uv run pytest server/tests/unit/analysis/test_biomechanics_metrics.py -q
```

Commit subject:

```text
feat(analysis): [S14-14] biomechanics metrics
```

Докази: `.workflow/evidence/S14-14.json`; фактичний SHA повідомляється після commit.

Навчання: обрати один невеликий фрагмент із [навчальної послідовності](../../docs/learning/README.md). Користувач пише власну ділянку; агент не перезаписує її й перевіряє перед інтеграцією.
