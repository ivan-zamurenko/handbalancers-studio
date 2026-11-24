# S14-10 — Описати версійну методику стійки збоку

**Статус документа:** погоджена картка; фактичне виконання тільки у `.workflow/state.json`.

HandstandSideView MethodVersion із видимими критеріями та межами висновків.

| Поле | Значення |
|---|---|
| Основний відповідальний | Biomechanics |
| Складність | M |
| Залежить від | S06-07 |
| Локальні gates | Немає; реальні дані/провайдери — за чинними owner-gates |

## Контекст і межі

- `docs/ai-coaching.md`
- `docs/contracts.md`
- `docs/owner-gates.md`

Входи: Вправа, методика власника, перевірені джерела й requirements до відео.

Виходи: HandstandSideView MethodVersion із видимими критеріями та межами висновків.

## Файли відповідальності

- `server/studio/analysis/handstand.py`
- `server/studio/analysis/methods.py`
- `server/tests/integration/analysis/test_handstand_method.py`

Це майбутні шляхи, не твердження про наявність реалізації. Міграція створюється лише перед першою командою, яка її використовує; номер береться від фактичного Alembic head. Інтегратор одноосібно редагує міграції/state. Чужі модулі — тільки через погоджений контракт.

## Перевірювані сценарії

| Сценарій | Очікуваний результат |
|---|---|
| `published_method` | Методика має exercise/version/camera requirements/criteria і автора погодження; published version immutable. |
| `no_invented_thresholds` | Без погоджених task-specific порогів automatic criterion не активний; загальна норма для всіх людей не вигадується. |
| `observability_limits` | Звичайні landmarks не видаються за вимір попереку/лопаток чи м’язової сили; wrist/ribcage лише де видно й валідовано. |
| `wrong_exercise_view` | Інша вправа, ракурс або непідтриманий критерій дає needs_input/unsupported. |

## HTTP / компонентний контракт

Внутрішній MethodVersion; API publication використовує чинні owner guards.

## Дані

Версії методик і критеріїв; зв’язок з exercise version. Assessment criterion reference лише за потреби; не дублювати S12.

## Виконання та Definition of Done

1. Перевірити prerequisites, фактичний scope і поточні API/DB contracts. Для коду — тест сценарію, спостережуваний RED з правильної причини, мінімальна реалізація, GREEN. Для документації/дослідження — validator або reproducible evaluation, без фіктивних тестів.
2. Виконати вузьку перевірку нижче, потім affected-module suite. DB/RLS/concurrency — на реальному ізольованому PostgreSQL. UI — особистий перегляд актуальних screenshots за AGENTS.md; навчальні приклади лише synthetic.
3. Перевірити owner/permission/entitlement, обмеження ресурсів, приватність і відмови. Немає реального стенда/дозволу — env_blocked у evidence; mock не підтверджує provider quality.
4. Незалежний read-only review; оновити CURRENT/state/evidence, один GREEN commit у чинній task/execution-v4. Push лише підтвердженому origin; без merge/deploy/hosted migrations.

Команда після створення відповідного тесту/harness:

```sh
uv run pytest server/tests/integration/analysis/test_handstand_method.py -q
```

Commit subject:

```text
feat(analysis): [S14-10] handstand method
```

Докази: `.workflow/evidence/S14-10.json`; фактичний SHA повідомляється після commit.

Навчання: обрати один невеликий фрагмент із [навчальної послідовності](../../docs/learning/README.md). Користувач пише власну ділянку; агент не перезаписує її й перевіряє перед інтеграцією.
