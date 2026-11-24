# S10-13 — Додати відео одного підходу в C3

**Статус документа:** погоджена картка; фактичне виконання тільки у `.workflow/state.json`.

Зрозумілий UI запису/завантаження одного контрольного підходу в наявній оболонці.

| Поле | Значення |
|---|---|
| Основний відповідальний | Frontend |
| Складність | M |
| Залежить від | S10-12, S09-07, S06-07 |
| Локальні gates | Немає; реальні дані/провайдери — за чинними owner-gates |

## Контекст і межі

- `docs/ai-coaching.md`
- `docs/contracts.md`
- `docs/owner-gates.md`

Входи: C3, exercise demonstration, media API.

Виходи: Зрозумілий UI запису/завантаження одного контрольного підходу в наявній оболонці.

## Файли відповідальності

- `server/templates/training/`
- `server/static/js/training/`
- `tests/e2e/exercise_video_upload_ui.spec.js`

Це майбутні шляхи, не твердження про наявність реалізації. Міграція створюється лише перед першою командою, яка її використовує; номер береться від фактичного Alembic head. Інтегратор одноосібно редагує міграції/state. Чужі модулі — тільки через погоджений контракт.

## Перевірювані сценарії

| Сценарій | Очікуваний результат |
|---|---|
| `example_and_upload` | Приклад та завантаження/запис доступні всередині конкретної вправи; native file/camera capture із fallback file picker. |
| `retry_preserves_input` | Втрата мережі, відмова camera, expired intent і validation error не очищають set logs; retry зрозумілий. |
| `no_video_completion` | Можна завершити заняття без відео; technique лишається unreviewed. |
| `visual_states` | Особисто перевірено 1440/390/320, light/dark, UA/EN, keyboard, upload/empty/error/loaded states. |

## HTTP / компонентний контракт

Використовує upload intent/finalize та чинне video attachment API; browser не визначає доступ.

## Дані

Немає DDL.

## Виконання та Definition of Done

1. Перевірити prerequisites, фактичний scope і поточні API/DB contracts. Для коду — тест сценарію, спостережуваний RED з правильної причини, мінімальна реалізація, GREEN. Для документації/дослідження — validator або reproducible evaluation, без фіктивних тестів.
2. Виконати вузьку перевірку нижче, потім affected-module suite. DB/RLS/concurrency — на реальному ізольованому PostgreSQL. UI — особистий перегляд актуальних screenshots за AGENTS.md; навчальні приклади лише synthetic.
3. Перевірити owner/permission/entitlement, обмеження ресурсів, приватність і відмови. Немає реального стенда/дозволу — env_blocked у evidence; mock не підтверджує provider quality.
4. Незалежний read-only review; оновити CURRENT/state/evidence, один GREEN commit у чинній task/execution-v4. Push лише підтвердженому origin; без merge/deploy/hosted migrations.

Команда після створення відповідного тесту/harness:

```sh
npx playwright test tests/e2e/exercise_video_upload_ui.spec.js
```

Commit subject:

```text
feat(media): [S10-13] exercise video upload ui
```

Докази: `.workflow/evidence/S10-13.json`; фактичний SHA повідомляється після commit.

Навчання: обрати один невеликий фрагмент із [навчальної послідовності](../../docs/learning/README.md). Користувач пише власну ділянку; агент не перезаписує її й перевіряє перед інтеграцією.
