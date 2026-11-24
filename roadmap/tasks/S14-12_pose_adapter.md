# S14-12 — Підключити перший перевірений pose adapter

**Статус документа:** погоджена картка; фактичне виконання тільки у `.workflow/state.json`.

Перший реальний адаптер в окремому worker-процесі того самого застосунку.

| Поле | Значення |
|---|---|
| Основний відповідальний | Computer Vision |
| Складність | L |
| Залежить від | S14-11 |
| Локальні gates | Немає; реальні дані/провайдери — за чинними owner-gates |

## Контекст і межі

- `docs/ai-coaching.md`
- `docs/contracts.md`
- `docs/owner-gates.md`

Входи: PoseAdapter contract і рішення S14-00 про конкретну модель.

Виходи: Перший реальний адаптер в окремому worker-процесі того самого застосунку.

## Файли відповідальності

- `server/studio/analysis/pose_mediapipe.py`
- `server/studio/analysis/video_preprocessing.py`
- `server/studio/jobs/analysis_worker.py`
- `server/tests/integration/analysis/test_pose_adapter.py`

Це майбутні шляхи, не твердження про наявність реалізації. Міграція створюється лише перед першою командою, яка її використовує; номер береться від фактичного Alembic head. Інтегратор одноосібно редагує міграції/state. Чужі модулі — тільки через погоджений контракт.

## Перевірювані сценарії

| Сценарій | Очікуваний результат |
|---|---|
| `actual_allowed_video` | Реальні дозволені кліпи проходять pinned модель; unit fake не є quality evidence. |
| `inverted_rotation_timeline` | Перевірено upside-down, phone rotation, variable frame rate; landmarks прив’язані до часу вихідного кліпу. |
| `resource_and_integrity` | Обмежені decode/inference час, RAM, frames; неповний/невірний hash не приймається. |
| `durable_execution` | Crash/retry/lease з S14-03 не множить результати; permissions повторно перевіряються перед читанням/публікацією. |

## HTTP / компонентний контракт

Реалізація PoseAdapter; job stage/progress через чинний analysis status.

## Дані

Версія pose artifact і processing metadata; нова revision лише для потрібних полів.

## Виконання та Definition of Done

1. Перевірити prerequisites, фактичний scope і поточні API/DB contracts. Для коду — тест сценарію, спостережуваний RED з правильної причини, мінімальна реалізація, GREEN. Для документації/дослідження — validator або reproducible evaluation, без фіктивних тестів.
2. Виконати вузьку перевірку нижче, потім affected-module suite. DB/RLS/concurrency — на реальному ізольованому PostgreSQL. UI — особистий перегляд актуальних screenshots за AGENTS.md; навчальні приклади лише synthetic.
3. Перевірити owner/permission/entitlement, обмеження ресурсів, приватність і відмови. Немає реального стенда/дозволу — env_blocked у evidence; mock не підтверджує provider quality.
4. Незалежний read-only review; оновити CURRENT/state/evidence, один GREEN commit у чинній task/execution-v4. Push лише підтвердженому origin; без merge/deploy/hosted migrations.

Команда після створення відповідного тесту/harness:

```sh
uv run pytest server/tests/integration/analysis/test_pose_adapter.py -q
```

Commit subject:

```text
feat(analysis): [S14-12] pose adapter
```

Докази: `.workflow/evidence/S14-12.json`; фактичний SHA повідомляється після commit.

Навчання: обрати один невеликий фрагмент із [навчальної послідовності](../../docs/learning/README.md). Користувач пише власну ділянку; агент не перезаписує її й перевіряє перед інтеграцією.

## Уточнення

MediaPipe default candidate. Якщо S14-00 обґрунтовано вибирає RTMPose, спочатку оновити шлях адаптера/lock/ADR; не підключати обидва наперед.
