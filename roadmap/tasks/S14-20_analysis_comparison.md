# S14-20 — Порівнювати лише сумісні аналізи

**Статус документа:** погоджена картка; фактичне виконання тільки у `.workflow/state.json`.

Прогрес техніки зі зрозумілими обмеженнями сумісності.

| Поле | Значення |
|---|---|
| Основний відповідальний | Backend |
| Складність | M |
| Залежить від | S14-19, S09-09 |
| Локальні gates | Немає; реальні дані/провайдери — за чинними owner-gates |

## Контекст і межі

- `docs/ai-coaching.md`
- `docs/contracts.md`
- `docs/owner-gates.md`

Входи: Версійні звіти й чинна історія виконань.

Виходи: Прогрес техніки зі зрозумілими обмеженнями сумісності.

## Файли відповідальності

- `server/studio/progress/analysis.py`
- `server/templates/member/progress.html`
- `tests/e2e/analysis_comparison.spec.js`
- `server/tests/integration/progress/test_analysis_comparison.py`

Це майбутні шляхи, не твердження про наявність реалізації. Міграція створюється лише перед першою командою, яка її використовує; номер береться від фактичного Alembic head. Інтегратор одноосібно редагує міграції/state. Чужі модулі — тільки через погоджений контракт.

## Перевірювані сценарії

| Сценарій | Очікуваний результат |
|---|---|
| `comparable_versions` | Порівняння перевіряє method/metric/pose/preprocessing versions, view/side/units/normalization; несумісність явна. |
| `no_false_trend` | Низька якість/відсутність даних не означає покращення чи погіршення; job retry не додає прогрес. |
| `own_bounded_history` | Лише власна історія, bounded pagination; особисті метрики не агрегуються в загальний knowledge corpus. |
| `reprocessing_explicit` | Повторна обробка лише за актуальним дозволом створює новий результат; старий звіт збережений. |
| `visual_comparison_states` | Особистий browser review UA/EN, 1440/390, light/dark, loaded/empty/incompatible/needs_input; keyboard та 320 для змін ширини. |

## HTTP / компонентний контракт

Owner-scoped comparison read projection у чинному progress API; лише сумісні metric IDs.

## Дані

Похідна read projection із results, не друге джерело тренувальних фактів; індекси за owner/exercise/time.

## Виконання та Definition of Done

1. Перевірити prerequisites, фактичний scope і поточні API/DB contracts. Для коду — тест сценарію, спостережуваний RED з правильної причини, мінімальна реалізація, GREEN. Для документації/дослідження — validator або reproducible evaluation, без фіктивних тестів.
2. Виконати вузьку перевірку нижче, потім affected-module suite. DB/RLS/concurrency — на реальному ізольованому PostgreSQL. UI — особистий перегляд актуальних screenshots за AGENTS.md; навчальні приклади лише synthetic.
3. Перевірити owner/permission/entitlement, обмеження ресурсів, приватність і відмови. Немає реального стенда/дозволу — env_blocked у evidence; mock не підтверджує provider quality.
4. Незалежний read-only review; оновити CURRENT/state/evidence, один GREEN commit у чинній task/execution-v4. Push лише підтвердженому origin; без merge/deploy/hosted migrations.

Команда після створення відповідного тесту/harness:

```sh
uv run pytest server/tests/integration/progress/test_analysis_comparison.py -q && npx playwright test tests/e2e/analysis_comparison.spec.js
```

Commit subject:

```text
feat(progress): [S14-20] analysis comparison
```

Докази: `.workflow/evidence/S14-20.json`; фактичний SHA повідомляється після commit.

Навчання: обрати один невеликий фрагмент із [навчальної послідовності](../../docs/learning/README.md). Користувач пише власну ділянку; агент не перезаписує її й перевіряє перед інтеграцією.
