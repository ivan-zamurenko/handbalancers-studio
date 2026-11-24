# S06-07 — Прив’язати приклад виконання до версії вправи

**Статус документа:** погоджена картка; фактичне виконання тільки у `.workflow/state.json`.

Версійний приклад для C3 без зміни старих призначень.

| Поле | Значення |
|---|---|
| Основний відповідальний | Backend |
| Складність | M |
| Залежить від | S06-03, S06-05 |
| Локальні gates | Немає; реальні дані/провайдери — за чинними owner-gates |

## Контекст і межі

- `docs/ai-coaching.md`
- `docs/contracts.md`
- `docs/owner-gates.md`

Входи: Published exercise version і дозволене демонстраційне медіа.

Виходи: Версійний приклад для C3 без зміни старих призначень.

## Файли відповідальності

- `server/studio/catalog/demonstrations.py`
- `server/tests/integration/catalog/test_exercise_demonstration.py`

Це майбутні шляхи, не твердження про наявність реалізації. Міграція створюється лише перед першою командою, яка її використовує; номер береться від фактичного Alembic head. Інтегратор одноосібно редагує міграції/state. Чужі модулі — тільки через погоджений контракт.

## Перевірювані сценарії

| Сценарій | Очікуваний результат |
|---|---|
| `published_example` | Published exercise version фіксує дозволений приклад та інструкцію. |
| `old_example_immutable` | Заміна прикладу не переписує опубліковану версію або старий snapshot. |
| `unavailable_example` | Недоступний приклад явно позначено; приватні ролики клієнтів не стають прикладами. |

## HTTP / компонентний контракт

Розширити чинний exercise read DTO даними прикладу; окремого каталогу не створювати.

## Дані

Адитивне посилання на приклад у версії вправи; фактична наступна Alembic revision.

## Виконання та Definition of Done

1. Перевірити prerequisites, фактичний scope і поточні API/DB contracts. Для коду — тест сценарію, спостережуваний RED з правильної причини, мінімальна реалізація, GREEN. Для документації/дослідження — validator або reproducible evaluation, без фіктивних тестів.
2. Виконати вузьку перевірку нижче, потім affected-module suite. DB/RLS/concurrency — на реальному ізольованому PostgreSQL. UI — особистий перегляд актуальних screenshots за AGENTS.md; навчальні приклади лише synthetic.
3. Перевірити owner/permission/entitlement, обмеження ресурсів, приватність і відмови. Немає реального стенда/дозволу — env_blocked у evidence; mock не підтверджує provider quality.
4. Незалежний read-only review; оновити CURRENT/state/evidence, один GREEN commit у чинній task/execution-v4. Push лише підтвердженому origin; без merge/deploy/hosted migrations.

Команда після створення відповідного тесту/harness:

```sh
uv run pytest server/tests/integration/catalog/test_exercise_demonstration.py -q
```

Commit subject:

```text
feat(catalog): [S06-07] exercise demonstration
```

Докази: `.workflow/evidence/S06-07.json`; фактичний SHA повідомляється після commit.

Навчання: обрати один невеликий фрагмент із [навчальної послідовності](../../docs/learning/README.md). Користувач пише власну ділянку; агент не перезаписує її й перевіряє перед інтеграцією.
