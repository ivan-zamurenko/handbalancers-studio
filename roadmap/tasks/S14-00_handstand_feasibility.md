# S14-00 — Перевірити мінімальний CV/AI стек на дозволених прикладах

**Статус документа:** погоджена картка; фактичне виконання тільки у `.workflow/state.json`.

Відтворюваний звіт із вибором одного CV/LLM кандидата, версіями, ліцензіями, обмеженнями та виміряними результатами.

| Поле | Значення |
|---|---|
| Основний відповідальний | Principal Architect |
| Складність | L |
| Залежить від | S00-02, S00-09 |
| Локальні gates | Немає; реальні дані/провайдери — за чинними owner-gates |

## Контекст і межі

- `docs/ai-coaching.md`
- `docs/contracts.md`
- `docs/owner-gates.md`

Входи: Дозволений dataset manifest, task-specific критерії прийнятності, цільове середовище; бюджет LLM перед фактичними викликами.

Виходи: Відтворюваний звіт із вибором одного CV/LLM кандидата, версіями, ліцензіями, обмеженнями та виміряними результатами.

## Файли відповідальності

- `tools/evaluate_handstand.py`
- `docs/verification/handstand-feasibility.md`
- `tools/evaluate_handstand.py`

Це майбутні шляхи, не твердження про наявність реалізації. Міграція створюється лише перед першою командою, яка її використовує; номер береться від фактичного Alembic head. Інтегратор одноосібно редагує міграції/state. Чужі модулі — тільки через погоджений контракт.

## Перевірювані сценарії

| Сценарій | Очікуваний результат |
|---|---|
| `separate_evaluations` | Окремі CV і LLM результати; smoke не видається за точність чи готовність. |
| `rights_and_holdout` | Права на кліпи/моделі/ваги зафіксовані; held-out люди/кліпи не використані для підбору правил. |
| `quality_and_resources` | На стійці збоку виміряні помилки, відмови, latency, RAM і витрати; прийнятність погоджена, не вигадана. |
| `minimal_selection` | MediaPipe перший кандидат; RTMPose лише за недостатньої якості. Один LLM; SQL retrieval baseline. |
| `environment_explicit` | Перевірені Python 3.13/target OS та pinned artifacts; відсутній dataset/budget означає env_blocked, не passed. |

## HTTP / компонентний контракт

Немає продуктового API. CLI читає дозволений manifest і пише приватні результати перевірки.

## Дані

Немає DDL або доступу до клієнтських даних.

## Виконання та Definition of Done

1. Перевірити prerequisites, фактичний scope і поточні API/DB contracts. Для коду — тест сценарію, спостережуваний RED з правильної причини, мінімальна реалізація, GREEN. Для документації/дослідження — validator або reproducible evaluation, без фіктивних тестів.
2. Виконати вузьку перевірку нижче, потім affected-module suite. DB/RLS/concurrency — на реальному ізольованому PostgreSQL. UI — особистий перегляд актуальних screenshots за AGENTS.md; навчальні приклади лише synthetic.
3. Перевірити owner/permission/entitlement, обмеження ресурсів, приватність і відмови. Немає реального стенда/дозволу — env_blocked у evidence; mock не підтверджує provider quality.
4. Незалежний read-only review; оновити CURRENT/state/evidence, один GREEN commit у чинній task/execution-v4. Push лише підтвердженому origin; без merge/deploy/hosted migrations.

Команда після створення відповідного тесту/harness:

```sh
uv run python tools/evaluate_handstand.py --manifest <approved-manifest> --output private-evidence/handstand-evaluation
```

Commit subject:

```text
feat(analysis): [S14-00] handstand feasibility
```

Докази: `.workflow/evidence/S14-00.json`; фактичний SHA повідомляється після commit.

Навчання: обрати один невеликий фрагмент із [навчальної послідовності](../../docs/learning/README.md). Користувач пише власну ділянку; агент не перезаписує її й перевіряє перед інтеграцією.

## Уточнення

Дослідження офіційних docs вже є у docs/ai-coaching.md; ця картка перевіряє виконання, не повторює вебогляд. Команду запускати лише після створення harness і надання дозволеного manifest.
