# S10-14 — Видаляти приватне медіа та його похідні

**Статус документа:** погоджена картка; фактичне виконання тільки у `.workflow/state.json`.

Відновлюване видалення без спільної транзакції PostgreSQL/Storage.

| Поле | Значення |
|---|---|
| Основний відповідальний | Security |
| Складність | L |
| Залежить від | S10-12, S14-03 |
| Локальні gates | Немає; реальні дані/провайдери — за чинними owner-gates |

## Контекст і межі

- `docs/ai-coaching.md`
- `docs/contracts.md`
- `docs/owner-gates.md`

Входи: Media version, permissions, перелік derivative artifacts, durable jobs.

Виходи: Відновлюване видалення без спільної транзакції PostgreSQL/Storage.

## Файли відповідальності

- `server/studio/media/lifecycle.py`
- `server/studio/jobs/media_cleanup.py`
- `server/tests/integration/media/test_media_lifecycle.py`

Це майбутні шляхи, не твердження про наявність реалізації. Міграція створюється лише перед першою командою, яка її використовує; номер береться від фактичного Alembic head. Інтегратор одноосібно редагує міграції/state. Чужі модулі — тільки через погоджений контракт.

## Перевірювані сценарії

| Сценарій | Очікуваний результат |
|---|---|
| `revoke_during_job` | Revocation/delete між claim/read/send забороняє наступний крок; пізній результат не публікується. |
| `stale_worker_fenced` | Прострочений lease або generation не дозволяє відновити artifact після видалення. |
| `partial_failure_recovery` | DB tombstone та Storage delete відновлюються після часткового збою; retry обмежений і спостережуваний. |
| `all_derivatives` | Original, normalized, pose, thumbnail, temp та orphan upload охоплені lifecycle; чужі objects не зачіпаються. |
| `signed_url_window` | Задокументовано строк дії й залишкове вікно signed URL; не обіцяти миттєве відкликання вже виданого доступу. |

## HTTP / компонентний контракт

Чинна контрольована remove action: негайний tombstone і статус асинхронного очищення; повтор безпечний.

## Дані

Lifecycle/deletion generation і bounded cleanup intents; provenance tombstones; політика зберігання звітів окрема, не безстрокова.

## Виконання та Definition of Done

1. Перевірити prerequisites, фактичний scope і поточні API/DB contracts. Для коду — тест сценарію, спостережуваний RED з правильної причини, мінімальна реалізація, GREEN. Для документації/дослідження — validator або reproducible evaluation, без фіктивних тестів.
2. Виконати вузьку перевірку нижче, потім affected-module suite. DB/RLS/concurrency — на реальному ізольованому PostgreSQL. UI — особистий перегляд актуальних screenshots за AGENTS.md; навчальні приклади лише synthetic.
3. Перевірити owner/permission/entitlement, обмеження ресурсів, приватність і відмови. Немає реального стенда/дозволу — env_blocked у evidence; mock не підтверджує provider quality.
4. Незалежний read-only review; оновити CURRENT/state/evidence, один GREEN commit у чинній task/execution-v4. Push лише підтвердженому origin; без merge/deploy/hosted migrations.

Команда після створення відповідного тесту/harness:

```sh
uv run pytest server/tests/integration/media/test_media_lifecycle.py -q
```

Commit subject:

```text
feat(media): [S10-14] media lifecycle
```

Докази: `.workflow/evidence/S10-14.json`; фактичний SHA повідомляється після commit.

Навчання: обрати один невеликий фрагмент із [навчальної послідовності](../../docs/learning/README.md). Користувач пише власну ділянку; агент не перезаписує її й перевіряє перед інтеграцією.
