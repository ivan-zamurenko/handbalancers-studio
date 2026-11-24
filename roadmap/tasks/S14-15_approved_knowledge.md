# S14-15 — Опублікувати вузьку базу перевірених знань

**Статус документа:** погоджена картка; фактичне виконання тільки у `.workflow/state.json`.

Невеликий затверджений корпус стійки з простежуваними джерелами.

| Поле | Значення |
|---|---|
| Основний відповідальний | Knowledge Engineer |
| Складність | M |
| Залежить від | S06-03 |
| Локальні gates | Немає; реальні дані/провайдери — за чинними owner-gates |

## Контекст і межі

- `docs/ai-coaching.md`
- `docs/contracts.md`
- `docs/owner-gates.md`

Входи: Дозволені джерела і published exercise versions.

Виходи: Невеликий затверджений корпус стійки з простежуваними джерелами.

## Файли відповідальності

- `server/studio/knowledge/models.py`
- `server/studio/knowledge/service.py`
- `server/tests/integration/knowledge/test_approved_knowledge.py`

Це майбутні шляхи, не твердження про наявність реалізації. Міграція створюється лише перед першою командою, яка її використовує; номер береться від фактичного Alembic head. Інтегратор одноосібно редагує міграції/state. Чужі модулі — тільки через погоджений контракт.

## Перевірювані сценарії

| Сценарій | Очікуваний результат |
|---|---|
| `source_provenance` | Кожен фрагмент має source/author/date-if-known/license/evidence classification і version; недозволені копії не імпортуються. |
| `published_only` | Draft/revoked джерела не доступні новому retrieval; publication потребує owner authority. |
| `private_separation` | Відео, private notes і персональні факти не потрапляють у спільний корпус. |
| `exercise_metadata` | Затверджені вправи містять purpose/prerequisites/equipment/progression/regression/cues/constraints/source refs; claims не вигадуються. |

## HTTP / компонентний контракт

Owner-only draft/publish/revoke knowledge commands; спільний каталог вправ лишається джерелом exercise IDs.

## Дані

Sources, document/chunk versions, tags і exercise/criterion links у PostgreSQL. Без pgvector/embeddings на цьому етапі.

## Виконання та Definition of Done

1. Перевірити prerequisites, фактичний scope і поточні API/DB contracts. Для коду — тест сценарію, спостережуваний RED з правильної причини, мінімальна реалізація, GREEN. Для документації/дослідження — validator або reproducible evaluation, без фіктивних тестів.
2. Виконати вузьку перевірку нижче, потім affected-module suite. DB/RLS/concurrency — на реальному ізольованому PostgreSQL. UI — особистий перегляд актуальних screenshots за AGENTS.md; навчальні приклади лише synthetic.
3. Перевірити owner/permission/entitlement, обмеження ресурсів, приватність і відмови. Немає реального стенда/дозволу — env_blocked у evidence; mock не підтверджує provider quality.
4. Незалежний read-only review; оновити CURRENT/state/evidence, один GREEN commit у чинній task/execution-v4. Push лише підтвердженому origin; без merge/deploy/hosted migrations.

Команда після створення відповідного тесту/harness:

```sh
uv run pytest server/tests/integration/knowledge/test_approved_knowledge.py -q
```

Commit subject:

```text
feat(knowledge): [S14-15] approved knowledge
```

Докази: `.workflow/evidence/S14-15.json`; фактичний SHA повідомляється після commit.

Навчання: обрати один невеликий фрагмент із [навчальної послідовності](../../docs/learning/README.md). Користувач пише власну ділянку; агент не перезаписує її й перевіряє перед інтеграцією.
