# S00-09 — Закріпити простий AI-roadmap і навчання власника

**Статус документа:** погоджена картка; фактичне виконання тільки у `.workflow/state.json`.

Додати 20 майбутніх карток, мінімальний стек, правила даних і навчання без зміни runtime.

| Поле | Значення |
|---|---|
| Основний відповідальний | Integrator |
| Складність | M |
| Залежить від | S00-08 |
| Локальні gates | Немає; реальні дані/провайдери — за чинними owner-gates |

## Контекст і межі

- `docs/ai-coaching.md`
- `docs/learning/01-duration.md`
- `docs/decisions.md`

Входи: Погоджений власником план 2026-11-24 та чинний roadmap.

Виходи: Узгоджений машинний/людський roadmap і перше завдання для початківця.

## Файли відповідальності

- `roadmap/tasks.json`
- `roadmap/ROADMAP.md`
- `roadmap/MILESTONES.md`
- `docs/ai-coaching.md`
- `docs/learning/01-duration.md`
- `tools/tests/test_roadmap.py`

Це майбутні шляхи, не твердження про наявність реалізації. Міграція створюється лише перед першою командою, яка її використовує; номер береться від фактичного Alembic head. Інтегратор одноосібно редагує міграції/state. Чужі модулі — тільки через погоджений контракт.

## Перевірювані сценарії

| Сценарій | Очікуваний результат |
|---|---|
| `valid_dependency_graph` | Всі картки/read paths існують, DAG без циклів; 20 майбутніх функцій лишаються todo. |
| `preserve_existing_work` | Попередні completed definitions/state і gates незмінні; runtime/DDL не редагуються. |
| `machine_human_consistency` | Dependencies, API, DB, test cases і commands у нових картках відповідають JSON. |
| `simple_safe_learning` | SQL retrieval first, protected data/lifecycle, beginner exercise з перевірками без готового рішення. |

## HTTP / компонентний контракт

Продуктові API не змінюються; майбутні interfaces позначені як заплановані.

## Дані

DDL не виконується; номери майбутніх міграцій визначаються від фактичного head.

## Виконання та Definition of Done

1. Перевірити prerequisites, фактичний scope і поточні API/DB contracts. Для коду — тест сценарію, спостережуваний RED з правильної причини, мінімальна реалізація, GREEN. Для документації/дослідження — validator або reproducible evaluation, без фіктивних тестів.
2. Виконати вузьку перевірку нижче, потім affected-module suite. DB/RLS/concurrency — на реальному ізольованому PostgreSQL. UI — особистий перегляд актуальних screenshots за AGENTS.md; навчальні приклади лише synthetic.
3. Перевірити owner/permission/entitlement, обмеження ресурсів, приватність і відмови. Немає реального стенда/дозволу — env_blocked у evidence; mock не підтверджує provider quality.
4. Незалежний read-only review; оновити CURRENT/state/evidence, один GREEN commit у чинній task/execution-v4. Push лише підтвердженому origin; без merge/deploy/hosted migrations.

Команда після створення відповідного тесту/harness:

```sh
python tools/roadmap.py validate && python -m unittest discover -s tools/tests -p test_roadmap.py -v
```

Commit subject:

```text
docs(roadmap): [S00-09] plan incremental AI coaching and learning
```

Докази: `.workflow/evidence/S00-09.json`; фактичний SHA повідомляється після commit.

Навчання: обрати один невеликий фрагмент із [навчальної послідовності](../../docs/learning/README.md). Користувач пише власну ділянку; агент не перезаписує її й перевіряє перед інтеграцією.

## Уточнення

Це документаційна картка погодженого плану, не реалізація майбутніх 20 функцій.
