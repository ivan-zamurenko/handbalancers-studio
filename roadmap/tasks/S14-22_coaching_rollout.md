# S14-22 — Керувати поступовим увімкненням AI

**Статус документа:** погоджена картка; фактичне виконання тільки у `.workflow/state.json`.

Відтворюваний поступовий rollout із безпечним вимкненням.

| Поле | Значення |
|---|---|
| Основний відповідальний | QA |
| Складність | M |
| Залежить від | S14-07, S14-21, S10-14 |
| Локальні gates | Немає; реальні дані/провайдери — за чинними owner-gates |

## Контекст і межі

- `docs/ai-coaching.md`
- `docs/contracts.md`
- `docs/owner-gates.md`

Входи: Evaluation results, adaptation integration, media lifecycle і owner-approved gates.

Виходи: Відтворюваний поступовий rollout із безпечним вимкненням.

## Файли відповідальності

- `server/studio/analysis/rollout.py`
- `server/studio/settings.py`
- `docs/verification/ai-rollout.md`
- `server/tests/integration/analysis/test_coaching_rollout.py`

Це майбутні шляхи, не твердження про наявність реалізації. Міграція створюється лише перед першою командою, яка її використовує; номер береться від фактичного Alembic head. Інтегратор одноосібно редагує міграції/state. Чужі модулі — тільки через погоджений контракт.

## Перевірювані сценарії

| Сценарій | Очікуваний результат |
|---|---|
| `default_off` | Default off зберігає чинний training path; DB expansion не змушує вмикати AI. |
| `mode_boundaries` | off/shadow/report/proposal/auto мають server policy; shadow/report не застосовують план і не обходять processing/quality gates. |
| `fresh_guards` | Allowlist, budget, gates, capability і permissions перевірено перед кожною дією; kill switch зупиняє нові операції. |
| `safe_rollback` | Вимкнення не стирає history і не дає stale worker опублікувати результат; failed зовнішня перевірка лишається env_blocked. |
| `no_sale_claim` | Report milestone не означає готовність обіцяного Plus або дозвіл продажу; G_COMMERCE/G_PRODUCTION окремі. |

## HTTP / компонентний контракт

Внутрішня server rollout policy, без клієнтського role/tier/mode selector.

## Дані

Немає міграції за замовчуванням; використовувати перевірені config/gates.

## Виконання та Definition of Done

1. Перевірити prerequisites, фактичний scope і поточні API/DB contracts. Для коду — тест сценарію, спостережуваний RED з правильної причини, мінімальна реалізація, GREEN. Для документації/дослідження — validator або reproducible evaluation, без фіктивних тестів.
2. Виконати вузьку перевірку нижче, потім affected-module suite. DB/RLS/concurrency — на реальному ізольованому PostgreSQL. UI — особистий перегляд актуальних screenshots за AGENTS.md; навчальні приклади лише synthetic.
3. Перевірити owner/permission/entitlement, обмеження ресурсів, приватність і відмови. Немає реального стенда/дозволу — env_blocked у evidence; mock не підтверджує provider quality.
4. Незалежний read-only review; оновити CURRENT/state/evidence, один GREEN commit у чинній task/execution-v4. Push лише підтвердженому origin; без merge/deploy/hosted migrations.

Команда після створення відповідного тесту/harness:

```sh
uv run pytest server/tests/integration/analysis/test_coaching_rollout.py -q
```

Commit subject:

```text
feat(analysis): [S14-22] coaching rollout
```

Докази: `.workflow/evidence/S14-22.json`; фактичний SHA повідомляється після commit.

Навчання: обрати один невеликий фрагмент із [навчальної послідовності](../../docs/learning/README.md). Користувач пише власну ділянку; агент не перезаписує її й перевіряє перед інтеграцією.
