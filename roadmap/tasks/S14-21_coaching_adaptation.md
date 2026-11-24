# S14-21 — Передати рекомендації в чинний планувальник

**Статус документа:** погоджена картка; фактичне виконання тільки у `.workflow/state.json`.

Перевірена пропозиція наступних занять через спільний command layer.

| Поле | Значення |
|---|---|
| Основний відповідальний | Backend |
| Складність | L |
| Залежить від | S14-19, S11-05, S14-06 |
| Локальні gates | Немає; реальні дані/провайдери — за чинними owner-gates |

## Контекст і межі

- `docs/ai-coaching.md`
- `docs/contracts.md`
- `docs/owner-gates.md`

Входи: Recommendations, fresh plan/context revisions, затверджені правила S11.

Виходи: Перевірена пропозиція наступних занять через спільний command layer.

## Файли відповідальності

- `server/studio/analysis/adaptation.py`
- `server/studio/planning/apply.py`
- `server/tests/integration/analysis/test_coaching_adaptation.py`

Це майбутні шляхи, не твердження про наявність реалізації. Міграція створюється лише перед першою командою, яка її використовує; номер береться від фактичного Alembic head. Інтегратор одноосібно редагує міграції/state. Чужі модулі — тільки через погоджений контракт.

## Перевірювані сценарії

| Сценарій | Очікуваний результат |
|---|---|
| `future_only_preview` | Preview з approved recommendations змінює лише майбутнє; не completed/started sessions чи catalog. |
| `stale_context` | Новий факт, coach edit, video/method version чи відкликаний source робить стару пропозицію stale. |
| `shared_apply` | Пропозиція використовує чинні S14-06/S11-05; idempotency/rollback/concurrency перевірені реальною БД, окремий apply не створено. |
| `ownership_and_mode` | Effective entitlement/permission перевірено перед write; Pro/Pro+ лишається за coach, kill switch діє. |

## HTTP / компонентний контракт

Adapter Recommendations -> чинний AdaptationProposal/preview; рішення про autoapply належить S14-08/S14-22.

## Дані

Перевикористати proposal/plan revision і command receipts; нова таблиця лише за доведеної потреби.

## Виконання та Definition of Done

1. Перевірити prerequisites, фактичний scope і поточні API/DB contracts. Для коду — тест сценарію, спостережуваний RED з правильної причини, мінімальна реалізація, GREEN. Для документації/дослідження — validator або reproducible evaluation, без фіктивних тестів.
2. Виконати вузьку перевірку нижче, потім affected-module suite. DB/RLS/concurrency — на реальному ізольованому PostgreSQL. UI — особистий перегляд актуальних screenshots за AGENTS.md; навчальні приклади лише synthetic.
3. Перевірити owner/permission/entitlement, обмеження ресурсів, приватність і відмови. Немає реального стенда/дозволу — env_blocked у evidence; mock не підтверджує provider quality.
4. Незалежний read-only review; оновити CURRENT/state/evidence, один GREEN commit у чинній task/execution-v4. Push лише підтвердженому origin; без merge/deploy/hosted migrations.

Команда після створення відповідного тесту/harness:

```sh
uv run pytest server/tests/integration/analysis/test_coaching_adaptation.py -q
```

Commit subject:

```text
feat(analysis): [S14-21] coaching adaptation
```

Докази: `.workflow/evidence/S14-21.json`; фактичний SHA повідомляється після commit.

Навчання: обрати один невеликий фрагмент із [навчальної послідовності](../../docs/learning/README.md). Користувач пише власну ділянку; агент не перезаписує її й перевіряє перед інтеграцією.
