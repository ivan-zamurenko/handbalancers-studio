# S14-13 — Відхиляти непридатний запис і недостатні орієнтири

**Статус документа:** погоджена картка; фактичне виконання тільки у `.workflow/state.json`.

Перевірені інтервали й перелік дозволених до обчислення критеріїв.

| Поле | Значення |
|---|---|
| Основний відповідальний | Computer Vision |
| Складність | M |
| Залежить від | S14-12, S14-10 |
| Локальні gates | Немає; реальні дані/провайдери — за чинними owner-gates |

## Контекст і межі

- `docs/ai-coaching.md`
- `docs/contracts.md`
- `docs/owner-gates.md`

Входи: PoseSequence і MethodVersion.

Виходи: Перевірені інтервали й перелік дозволених до обчислення критеріїв.

## Файли відповідальності

- `server/studio/analysis/quality.py`
- `server/tests/unit/analysis/test_pose_quality.py`

Це майбутні шляхи, не твердження про наявність реалізації. Міграція створюється лише перед першою командою, яка її використовує; номер береться від фактичного Alembic head. Інтегратор одноосібно редагує міграції/state. Чужі модулі — тільки через погоджений контракт.

## Перевірювані сценарії

| Сценарій | Очікуваний результат |
|---|---|
| `bad_view_visibility` | Невірний ракурс, crop, occlusion, кілька людей або відсутність потрібних суглобів дають конкретну причину needs_input. |
| `per_metric_observability` | Частково придатний кліп не має одного оманливого confidence для всіх метрик. |
| `hold_interval` | Вхід/вихід зі стійки не змішуються з аналізом утримання; gaps і непевні intervals позначаються. |
| `no_fabricated_gaps` | Пропуски не заповнюються вигаданими впевненими вимірюваннями. |

## HTTP / компонентний контракт

QualityAssessment: usable intervals, per-criterion observability, reasons і suggested recording correction.

## Дані

Немає DDL. QualityAssessment — чистий DTO; його версійне збереження разом із метриками належить S14-19.

## Виконання та Definition of Done

1. Перевірити prerequisites, фактичний scope і поточні API/DB contracts. Для коду — тест сценарію, спостережуваний RED з правильної причини, мінімальна реалізація, GREEN. Для документації/дослідження — validator або reproducible evaluation, без фіктивних тестів.
2. Виконати вузьку перевірку нижче, потім affected-module suite. DB/RLS/concurrency — на реальному ізольованому PostgreSQL. UI — особистий перегляд актуальних screenshots за AGENTS.md; навчальні приклади лише synthetic.
3. Перевірити owner/permission/entitlement, обмеження ресурсів, приватність і відмови. Немає реального стенда/дозволу — env_blocked у evidence; mock не підтверджує provider quality.
4. Незалежний read-only review; оновити CURRENT/state/evidence, один GREEN commit у чинній task/execution-v4. Push лише підтвердженому origin; без merge/deploy/hosted migrations.

Команда після створення відповідного тесту/harness:

```sh
uv run pytest server/tests/unit/analysis/test_pose_quality.py -q
```

Commit subject:

```text
feat(analysis): [S14-13] pose quality
```

Докази: `.workflow/evidence/S14-13.json`; фактичний SHA повідомляється після commit.

Навчання: обрати один невеликий фрагмент із [навчальної послідовності](../../docs/learning/README.md). Користувач пише власну ділянку; агент не перезаписує її й перевіряє перед інтеграцією.
