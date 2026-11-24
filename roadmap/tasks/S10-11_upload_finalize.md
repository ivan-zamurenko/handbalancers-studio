# S10-11 — Перевірити файл і надійно завершити upload

**Статус документа:** погоджена картка; фактичне виконання тільки у `.workflow/state.json`.

ValidatedMediaAsset з незмінним hash, container, dimensions, duration і storage reference.

| Поле | Значення |
|---|---|
| Основний відповідальний | Backend |
| Складність | M |
| Залежить від | S10-10 |
| Локальні gates | Немає; реальні дані/провайдери — за чинними owner-gates |

## Контекст і межі

- `docs/ai-coaching.md`
- `docs/contracts.md`
- `docs/owner-gates.md`

Входи: UploadIntent і завершений приватний object.

Виходи: ValidatedMediaAsset з незмінним hash, container, dimensions, duration і storage reference.

## Файли відповідальності

- `server/studio/media/validation.py`
- `server/studio/media/uploads.py`
- `server/tests/integration/media/test_upload_finalize.py`

Це майбутні шляхи, не твердження про наявність реалізації. Міграція створюється лише перед першою командою, яка її використовує; номер береться від фактичного Alembic head. Інтегратор одноосібно редагує міграції/state. Чужі модулі — тільки через погоджений контракт.

## Перевірювані сценарії

| Сценарій | Очікуваний результат |
|---|---|
| `actual_bytes_checked` | Перевіряються фактичні MIME/container/size/duration/hash, не довірені browser metadata. |
| `incomplete_or_foreign` | Неповний, чужий або невідповідний object не стає evidence. |
| `decode_bounds` | Malformed media, надмірні dimensions/frame count, timeout/RAM limit завершуються контрольовано; мережеві протоколи decoder заборонені. |
| `finalize_idempotent` | Повтор finalize та збій між Storage і DB відновлюються без дублів; повторно перевірені owner/permissions/expiry. |

## HTTP / компонентний контракт

POST /api/media/uploads/{id}/complete: перевірений стан/metadata; no-store; не приймати довільний URL для fetch.

## Дані

Стани отримання/перевірки/готовності й checksum в upload intent; файли поза БД; наступна revision за потреби.

## Виконання та Definition of Done

1. Перевірити prerequisites, фактичний scope і поточні API/DB contracts. Для коду — тест сценарію, спостережуваний RED з правильної причини, мінімальна реалізація, GREEN. Для документації/дослідження — validator або reproducible evaluation, без фіктивних тестів.
2. Виконати вузьку перевірку нижче, потім affected-module suite. DB/RLS/concurrency — на реальному ізольованому PostgreSQL. UI — особистий перегляд актуальних screenshots за AGENTS.md; навчальні приклади лише synthetic.
3. Перевірити owner/permission/entitlement, обмеження ресурсів, приватність і відмови. Немає реального стенда/дозволу — env_blocked у evidence; mock не підтверджує provider quality.
4. Незалежний read-only review; оновити CURRENT/state/evidence, один GREEN commit у чинній task/execution-v4. Push лише підтвердженому origin; без merge/deploy/hosted migrations.

Команда після створення відповідного тесту/harness:

```sh
uv run pytest server/tests/integration/media/test_upload_finalize.py -q
```

Commit subject:

```text
feat(media): [S10-11] upload finalize
```

Докази: `.workflow/evidence/S10-11.json`; фактичний SHA повідомляється після commit.

Навчання: обрати один невеликий фрагмент із [навчальної послідовності](../../docs/learning/README.md). Користувач пише власну ділянку; агент не перезаписує її й перевіряє перед інтеграцією.
