# S14-16 — Вибирати затверджені знання простим SQL-пошуком

**Статус документа:** погоджена картка; фактичне виконання тільки у `.workflow/state.json`.

Малий релевантний контекст без приватних фактів і без RAG-фреймворку.

| Поле | Значення |
|---|---|
| Основний відповідальний | AI Engineer |
| Складність | M |
| Залежить від | S14-15, S14-14 |
| Локальні gates | Немає; реальні дані/провайдери — за чинними owner-gates |

## Контекст і межі

- `docs/ai-coaching.md`
- `docs/contracts.md`
- `docs/owner-gates.md`

Входи: Metric criterion IDs і approved knowledge.

Виходи: Малий релевантний контекст без приватних фактів і без RAG-фреймворку.

## Файли відповідальності

- `server/studio/knowledge/retrieval.py`
- `server/tests/integration/knowledge/test_knowledge_retrieval.py`

Це майбутні шляхи, не твердження про наявність реалізації. Міграція створюється лише перед першою командою, яка її використовує; номер береться від фактичного Alembic head. Інтегратор одноосібно редагує міграції/state. Чужі модулі — тільки через погоджений контракт.

## Перевірювані сценарії

| Сценарій | Очікуваний результат |
|---|---|
| `relevant_versioned_sources` | SQL filters exercise/criterion/publication і bounded text search дають релевантні реальні chunk IDs. |
| `revocation_cache` | Відкликана версія виключається навіть за stale cache; порожній результат явний. |
| `bounded_context` | Обмежені кількість/розмір фрагментів; джерело розглядається як дані, не інструкція моделі. |
| `ua_en_evaluation` | Перевірені питання UA/EN й expected source set; помилки retrieval виміряні до рішення про vectors. |

## HTTP / компонентний контракт

retrieve_knowledge(exercise_version, criterion_ids, locale) -> KnowledgeContext з versioned source refs.

## Дані

Metadata indexes і text search за потреби. pgvector лише за окремим рішенням після виміряної недостатності baseline.

## Виконання та Definition of Done

1. Перевірити prerequisites, фактичний scope і поточні API/DB contracts. Для коду — тест сценарію, спостережуваний RED з правильної причини, мінімальна реалізація, GREEN. Для документації/дослідження — validator або reproducible evaluation, без фіктивних тестів.
2. Виконати вузьку перевірку нижче, потім affected-module suite. DB/RLS/concurrency — на реальному ізольованому PostgreSQL. UI — особистий перегляд актуальних screenshots за AGENTS.md; навчальні приклади лише synthetic.
3. Перевірити owner/permission/entitlement, обмеження ресурсів, приватність і відмови. Немає реального стенда/дозволу — env_blocked у evidence; mock не підтверджує provider quality.
4. Незалежний read-only review; оновити CURRENT/state/evidence, один GREEN commit у чинній task/execution-v4. Push лише підтвердженому origin; без merge/deploy/hosted migrations.

Команда після створення відповідного тесту/harness:

```sh
uv run pytest server/tests/integration/knowledge/test_knowledge_retrieval.py -q
```

Commit subject:

```text
feat(knowledge): [S14-16] knowledge retrieval
```

Докази: `.workflow/evidence/S14-16.json`; фактичний SHA повідомляється після commit.

Навчання: обрати один невеликий фрагмент із [навчальної послідовності](../../docs/learning/README.md). Користувач пише власну ділянку; агент не перезаписує її й перевіряє перед інтеграцією.
