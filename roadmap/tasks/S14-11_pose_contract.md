# S14-11 — Визначити змінний pose adapter

**Статус документа:** погоджена картка; фактичне виконання тільки у `.workflow/state.json`.

PoseSequence: timestamps, canonical/native joints, visibility, координати, модель/config/transform versions.

| Поле | Значення |
|---|---|
| Основний відповідальний | Computer Vision |
| Складність | M |
| Залежить від | S14-04, S14-00 |
| Локальні gates | Немає; реальні дані/провайдери — за чинними owner-gates |

## Контекст і межі

- `docs/ai-coaching.md`
- `docs/contracts.md`
- `docs/owner-gates.md`

Входи: EvidenceManifest, ValidatedMediaAsset, versioned config.

Виходи: PoseSequence: timestamps, canonical/native joints, visibility, координати, модель/config/transform versions.

## Файли відповідальності

- `server/studio/analysis/pose.py`
- `server/tests/unit/analysis/test_pose_contract.py`

Це майбутні шляхи, не твердження про наявність реалізації. Міграція створюється лише перед першою командою, яка її використовує; номер береться від фактичного Alembic head. Інтегратор одноосібно редагує міграції/state. Чужі модулі — тільки через погоджений контракт.

## Перевірювані сценарії

| Сценарій | Очікуваний результат |
|---|---|
| `canonical_landmarks` | Native joint IDs мапляться явно; відсутній орієнтир = missing, не нуль чи вигадана точка. |
| `time_coordinate_metadata` | Timestamp, original/processed dimensions, rotation/transform, coordinate convention і units відомі. |
| `provider_independent` | Два contract fixtures різних schemas дають однаковий canonical DTO; downstream не імпортує SDK. |
| `confidence_not_accuracy` | Detector visibility/presence збережені окремо; не видаються за калібровану достовірність метрики. |

## HTTP / компонентний контракт

PoseAdapter.extract(validated_asset, config) -> PoseSequence; без тренерських рішень.

## Дані

Немає DDL. PoseSequence — DTO/серіалізований private artifact; manifest persistence належить S14-04/S14-12, результати — S14-19.

## Виконання та Definition of Done

1. Перевірити prerequisites, фактичний scope і поточні API/DB contracts. Для коду — тест сценарію, спостережуваний RED з правильної причини, мінімальна реалізація, GREEN. Для документації/дослідження — validator або reproducible evaluation, без фіктивних тестів.
2. Виконати вузьку перевірку нижче, потім affected-module suite. DB/RLS/concurrency — на реальному ізольованому PostgreSQL. UI — особистий перегляд актуальних screenshots за AGENTS.md; навчальні приклади лише synthetic.
3. Перевірити owner/permission/entitlement, обмеження ресурсів, приватність і відмови. Немає реального стенда/дозволу — env_blocked у evidence; mock не підтверджує provider quality.
4. Незалежний read-only review; оновити CURRENT/state/evidence, один GREEN commit у чинній task/execution-v4. Push лише підтвердженому origin; без merge/deploy/hosted migrations.

Команда після створення відповідного тесту/harness:

```sh
uv run pytest server/tests/unit/analysis/test_pose_contract.py -q
```

Commit subject:

```text
feat(analysis): [S14-11] pose contract
```

Докази: `.workflow/evidence/S14-11.json`; фактичний SHA повідомляється після commit.

Навчання: обрати один невеликий фрагмент із [навчальної послідовності](../../docs/learning/README.md). Користувач пише власну ділянку; агент не перезаписує її й перевіряє перед інтеграцією.
