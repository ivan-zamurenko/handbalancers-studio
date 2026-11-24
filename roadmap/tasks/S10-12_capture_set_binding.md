# S10-12 — Зв’язати відеоверсію з обраним підходом

**Статус документа:** погоджена картка; фактичне виконання тільки у `.workflow/state.json`.

Точна версія evidence для одного обраного підходу без вимоги відео кожного підходу.

| Поле | Значення |
|---|---|
| Основний відповідальний | Backend |
| Складність | M |
| Залежить від | S10-02, S10-11 |
| Локальні gates | Немає; реальні дані/провайдери — за чинними owner-gates |

## Контекст і межі

- `docs/ai-coaching.md`
- `docs/contracts.md`
- `docs/owner-gates.md`

Входи: ValidatedMediaAsset, submission, exercise snapshot і optional recorded set.

Виходи: Точна версія evidence для одного обраного підходу без вимоги відео кожного підходу.

## Файли відповідальності

- `server/studio/media/models.py`
- `server/studio/media/service.py`
- `server/studio/media/schemas.py`
- `server/tests/integration/media/test_capture_set_binding.py`

Це майбутні шляхи, не твердження про наявність реалізації. Міграція створюється лише перед першою командою, яка її використовує; номер береться від фактичного Alembic head. Інтегратор одноосібно редагує міграції/state. Чужі модулі — тільки через погоджений контракт.

## Перевірювані сценарії

| Сценарій | Очікуваний результат |
|---|---|
| `one_current_video` | Один submission на session_exercise збережено; новий файл створює immutable version. |
| `captured_set_owner` | captured_set_log_id, якщо заданий, належить цій вправі й власнику; skipped/чужий підхід відхилено. |
| `concurrent_replace` | Очікувана revision і locking дають один current pointer; старі evidence/reviews не переписуються. |
| `link_compatibility` | Чинний URL input підтримується; новий upload_id приймається лише після серверної перевірки ownership. |

## HTTP / компонентний контракт

Чинний POST /api/session-exercises/{id}/video: рівно один із url/upload_id, expected_revision, optional captured_set_log_id. Старий url payload валідний.

## Дані

Додати asset reference і nullable captured_set_log_id до immutable media version; composite owner constraints, зберегти unique(session_exercise_id).

## Виконання та Definition of Done

1. Перевірити prerequisites, фактичний scope і поточні API/DB contracts. Для коду — тест сценарію, спостережуваний RED з правильної причини, мінімальна реалізація, GREEN. Для документації/дослідження — validator або reproducible evaluation, без фіктивних тестів.
2. Виконати вузьку перевірку нижче, потім affected-module suite. DB/RLS/concurrency — на реальному ізольованому PostgreSQL. UI — особистий перегляд актуальних screenshots за AGENTS.md; навчальні приклади лише synthetic.
3. Перевірити owner/permission/entitlement, обмеження ресурсів, приватність і відмови. Немає реального стенда/дозволу — env_blocked у evidence; mock не підтверджує provider quality.
4. Незалежний read-only review; оновити CURRENT/state/evidence, один GREEN commit у чинній task/execution-v4. Push лише підтвердженому origin; без merge/deploy/hosted migrations.

Команда після створення відповідного тесту/harness:

```sh
uv run pytest server/tests/integration/media/test_capture_set_binding.py -q
```

Commit subject:

```text
feat(media): [S10-12] capture set binding
```

Докази: `.workflow/evidence/S10-12.json`; фактичний SHA повідомляється після commit.

Навчання: обрати один невеликий фрагмент із [навчальної послідовності](../../docs/learning/README.md). Користувач пише власну ділянку; агент не перезаписує її й перевіряє перед інтеграцією.
