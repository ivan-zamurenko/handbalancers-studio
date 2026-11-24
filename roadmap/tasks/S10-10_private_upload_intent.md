# S10-10 — Видати обмежений дозвіл приватного завантаження

**Статус документа:** погоджена картка; фактичне виконання тільки у `.workflow/state.json`.

UploadIntent: id, дозволений спосіб завантаження, строк дії та обмеження.

| Поле | Значення |
|---|---|
| Основний відповідальний | Backend |
| Складність | M |
| Залежить від | S09-02, S14-01, S14-02 |
| Локальні gates | Немає; реальні дані/провайдери — за чинними owner-gates |

## Контекст і межі

- `docs/ai-coaching.md`
- `docs/contracts.md`
- `docs/owner-gates.md`

Входи: Перевірений actor, exercise snapshot, processing permissions, Storage adapter.

Виходи: UploadIntent: id, дозволений спосіб завантаження, строк дії та обмеження.

## Файли відповідальності

- `server/studio/media/uploads.py`
- `server/studio/media/storage.py`
- `server/studio/media/routes.py`
- `server/tests/integration/media/test_private_upload_intent.py`

Це майбутні шляхи, не твердження про наявність реалізації. Міграція створюється лише перед першою командою, яка її використовує; номер береться від фактичного Alembic head. Інтегратор одноосібно редагує міграції/state. Чужі модулі — тільки через погоджений контракт.

## Перевірювані сценарії

| Сценарій | Очікуваний результат |
|---|---|
| `owner_permission` | Сервер перевіряє session_exercise owner, актуальну capability й окремий дозвіл processing; роль не береться з body. |
| `bounded_intent` | Сервер створює незмінний object key; строк, розмір, квота й кількість одночасних intent обмежені. |
| `idempotent_intent` | Повтор того самого ключа не створює новий intent; інший payload дає 409. |
| `private_token` | Bucket приватний, signed upload не дозволяє list/read/overwrite інших об’єктів; секрети не потрапляють у відповідь чи logs. |

## HTTP / компонентний контракт

POST /api/session-exercises/{id}/video/uploads: owner-bound upload intent і обмежена upload capability; CSRF/Origin/idempotency.

## Дані

Upload intents з owner/session_exercise/object key/state/expires_at; RLS, унікальність command key; наступна revision.

## Виконання та Definition of Done

1. Перевірити prerequisites, фактичний scope і поточні API/DB contracts. Для коду — тест сценарію, спостережуваний RED з правильної причини, мінімальна реалізація, GREEN. Для документації/дослідження — validator або reproducible evaluation, без фіктивних тестів.
2. Виконати вузьку перевірку нижче, потім affected-module suite. DB/RLS/concurrency — на реальному ізольованому PostgreSQL. UI — особистий перегляд актуальних screenshots за AGENTS.md; навчальні приклади лише synthetic.
3. Перевірити owner/permission/entitlement, обмеження ресурсів, приватність і відмови. Немає реального стенда/дозволу — env_blocked у evidence; mock не підтверджує provider quality.
4. Незалежний read-only review; оновити CURRENT/state/evidence, один GREEN commit у чинній task/execution-v4. Push лише підтвердженому origin; без merge/deploy/hosted migrations.

Команда після створення відповідного тесту/harness:

```sh
uv run pytest server/tests/integration/media/test_private_upload_intent.py -q
```

Commit subject:

```text
feat(media): [S10-10] private upload intent
```

Докази: `.workflow/evidence/S10-10.json`; фактичний SHA повідомляється після commit.

Навчання: обрати один невеликий фрагмент із [навчальної послідовності](../../docs/learning/README.md). Користувач пише власну ділянку; агент не перезаписує її й перевіряє перед інтеграцією.

## Уточнення

Supabase Storage + signed TUS — початковий шлях; actual provider/дані тільки після G_VIDEO/G_PRIVACY. Storage credentials серверні, без розширення DB-ролі web.
