# S14-17 — Пояснювати факти й відокремлювати гіпотези

**Статус документа:** погоджена картка; фактичне виконання тільки у `.workflow/state.json`.

Перевірене пояснення без права змінювати вимірювання або програму.

| Поле | Значення |
|---|---|
| Основний відповідальний | AI Engineer |
| Складність | L |
| Залежить від | S14-16, S14-05, S14-00 |
| Локальні gates | Немає; реальні дані/провайдери — за чинними owner-gates |

## Контекст і межі

- `docs/ai-coaching.md`
- `docs/contracts.md`
- `docs/owner-gates.md`

Входи: MetricResult[], KnowledgeContext, мінімальний серверний user context, дозволи/бюджет.

Виходи: Перевірене пояснення без права змінювати вимірювання або програму.

## Файли відповідальності

- `server/studio/analysis/coach.py`
- `server/studio/analysis/llm_gateway.py`
- `server/tests/integration/analysis/test_grounded_explanations.py`

Це майбутні шляхи, не твердження про наявність реалізації. Міграція створюється лише перед першою командою, яка її використовує; номер береться від фактичного Alembic head. Інтегратор одноосібно редагує міграції/state. Чужі модулі — тільки через погоджений контракт.

## Перевірювані сценарії

| Сценарій | Очікуваний результат |
|---|---|
| `grounded_claims` | Пояснення містить реальні metric/evidence/source IDs; вигадані значення/цитати відхилено. |
| `hypothesis_not_diagnosis` | Observed angle не підтверджує слабкість, обмеження рухливості чи травму; непідтверджена причина лишається гіпотезою. |
| `needs_assessment` | Коли потрібне уточнення, повертається затверджений assessment reference або needs_input, без вигаданого тесту. |
| `bounded_provider_failure` | Один provider, timeout/retry/token budget, refusal/invalid JSON/no sources обробляються без partial publish. |
| `minimal_private_context` | LLM отримує лише дозволені структуровані факти користувача й джерела; без відео, SQL, credentials або чужих даних. |

## HTTP / компонентний контракт

CoachExplanation: observations, hypotheses, source refs, assessment needs; Pydantic плюс domain validation.

## Дані

Structured explanation/versioned model+prompt+source manifest; raw sensitive prompt logging заборонений.

## Виконання та Definition of Done

1. Перевірити prerequisites, фактичний scope і поточні API/DB contracts. Для коду — тест сценарію, спостережуваний RED з правильної причини, мінімальна реалізація, GREEN. Для документації/дослідження — validator або reproducible evaluation, без фіктивних тестів.
2. Виконати вузьку перевірку нижче, потім affected-module suite. DB/RLS/concurrency — на реальному ізольованому PostgreSQL. UI — особистий перегляд актуальних screenshots за AGENTS.md; навчальні приклади лише synthetic.
3. Перевірити owner/permission/entitlement, обмеження ресурсів, приватність і відмови. Немає реального стенда/дозволу — env_blocked у evidence; mock не підтверджує provider quality.
4. Незалежний read-only review; оновити CURRENT/state/evidence, один GREEN commit у чинній task/execution-v4. Push лише підтвердженому origin; без merge/deploy/hosted migrations.

Команда після створення відповідного тесту/harness:

```sh
uv run pytest server/tests/integration/analysis/test_grounded_explanations.py -q
```

Commit subject:

```text
feat(analysis): [S14-17] grounded explanations
```

Докази: `.workflow/evidence/S14-17.json`; фактичний SHA повідомляється після commit.

Навчання: обрати один невеликий фрагмент із [навчальної послідовності](../../docs/learning/README.md). Користувач пише власну ділянку; агент не перезаписує її й перевіряє перед інтеграцією.
