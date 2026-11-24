# Канонические контракты v4

## Область
Ниже — инженерные уточнения утверждённого продукта. Вместе с карточками они имеют приоритет над несовместимыми полями v3. Полный OpenAPI генерируется из реализованных DTO, не создаётся фиктивно для ещё неработающих routes. `api-inventory.json` связывает контракты с задачами.

## Общие conventions
API под `/api`; GET читает, POST создаёт/исполняет команду, PATCH меняет draft, PUT сохраняет идентифицируемый объект. UUID не являются авторизацией. Для writes: trusted session + CSRF + role/ownership + entitlement + feature gate. Ошибка `{error:{code,message_key,field_errors:[],request_id}}`; 401 auth, 402 own paid action unavailable, 403 explicit forbidden action, 404 чужой private resource, 409 stale/duplicate-body-conflict, 422 schema, 429 limit, 503 dependency unavailable. Private data: Cache-Control:no-store.

Идемпотентность publish/start/complete/preview-apply/checkout: `Idempotency-Key` ограниченной длины, scoped actor+operation, body hash. Права проверяются и на replay. Повтор успешной команды с тем же телом возвращает тот же resource/result; другое тело с ключом —409. Хранение receipt в той же transaction, что effect, для локальных commands. Для network command durable intent → call → reconcile/finalize. Business unique guards остаются после очистки receipt.

`expected_revision` — имя поля wire API. Server response `revision` сообщает revision редактируемого объекта. В таблицах `row_version`; session completion использует `data_revision`, потому что проверяет весь набор фактов. DTO объясняет какая revision применима, нельзя случайно сравнить row и data versions.

## Publication
`POST /api/coach/exercises/{id}/publish {expected_revision}` → immutable exercise version. `POST /api/program-versions/{id}/publish {expected_revision}` → frozen program tree. Проверить все child IDs и версии. На program_version root lock распространяется вся child write operation, включая reordering и deletion. Draft edit не меняет published snapshot.

## Один план
training_plan.status active|paused|archived. Management mode self|ai|coach вычисляется из сервера; клиент не меняет mode. assignment_role **primary|assessment** (v3 `main` переименован в primary). Status pending|active|paused|completed|cancelled|superseded. UNIQUE current plan(user); UNIQUE current primary(plan) включает pending,active,paused. Assessment относится к тому же календарю, не второй основной программе.

scheduled_workout.origin_kind primary|additional|assessment. Status planned|in_progress|completed|skipped|missed|cancelled. Date `scheduled_for` обязательна, `scheduled_at` только если пользователь выбрал часы. Guided additional может иметь user_program_id=NULL, но source workout/version и plan/user обязательны. Source private/catalog всегда проверяется. Personal derivative не меняет общий шаблон.

## Preview / Apply
`POST /api/plans/{id}/previews` body:
```json
{"operation":"replace","source_program_workout_id":"UUID","source_program_version_id":"UUID","date":"2026-10-21","target_occurrence_id":"UUID","expected_plan_revision":3}
```
operation allowlist replace|add|move|change_primary|skip. Каждая имеет отдельный discriminated DTO: add не принимает чужой diff, change_primary требует version_id. Ответ:
```json
{"preview_id":"UUID","expires_at":"UTC timestamp","status":"compatible","plan_revision":3,"context_revision":18,"changes":[],"reasons":[],"alternatives":[]}
```
status compatible|conflict|insufficient_data. Даже compatible — результат правил, не медицинская гарантия. Changes содержит create/update/cancel с source и old/new date. Хранится server-produced payload/hash, pinned rules/permission/subscription/fact revisions. Client не отправляет изменённый changes при подтверждении.

`POST /api/plans/{id}/previews/{id}/apply {expected_plan_revision:3}` + key. Lock plan; verify actor, preview ownership/expiry, current permission/entitlement/rules/facts, untouched started/completed rows; apply whole diff; bump plan revision; audit; receipt. Stale context →409, пользователь получает новый preview. Авторизация не заменяется тем, что preview был когда-то разрешён.

При replace additional old primary не получает completed. Основная progression продвигается только подтверждённым фактом/явной owner-defined equivalence. Missed не копится как задолженность. Manual external activity учитывается как факт, но unknown load не становится zero.

## Start / log / complete
Start `POST /api/scheduled-workouts/{id}/start {expected_revision}` + key → session_id,revision,data_revision,snapshot. Повтор того же occurrence возвращает прежнюю session. Другой Start при active/paused session →409 active_session_exists, без второго snapshot.

`PUT /api/sessions/{id}/set-logs/{log_id}` содержит session_exercise_id,target_set_id,set_number,side,status,expected_revision и typed values. UUID создаётся клиентом однажды; slot уникален сервером. status completed|skipped; отсутствие строки означает not-recorded. Target значения положительные; actual explicit zero разрешён где tracking_kind допускает. Null ≠0≠skipped. Duration integer ms; load decimal kg; locale не меняет хранимые единицы. Пропуск не содержит придуманного actual value. Guided target совпадает с snapshot/source prescription. Responses не содержат приватных coach notes.

Session.status in_progress|paused|completed|abandoned. Pause/resume используют clock/time segments, серверный ordering/revision. Нет автоматического зачёта всего фонового времени. Rest между подходами внутри active session считается временем занятия; явная Pause исключается. Recovery после длительного background требует проверки/подтверждения, а не «магии таймера».

Complete `{expected_revision:<data_revision>,completion_kind:"full|partial",reason}` + key. Full означает: все необходимые слоты явно recorded как completed; actual может быть меньше target. Достижение целевого объёма — отдельная метрика, не подмена статуса сессии. Skipped/незаписанные не становятся full. Partial требует явного подтверждения состава; нули не дописываются. Atomic session+occurrence+report; review task side effect вводится в S10 и тоже тестируется. Replay не удваивает прогресс. Нет видео — technique_status unreviewed. Abandon переводит started occurrence в cancelled с reason=session_abandoned, сохраняет факты и не начисляет completed minutes. Обычные edits terminal session запрещены. Исправления исторического результата — отдельная будущая audited задача; в этом baseline такого UI нет.

## Offline
Можно продолжать только ранее начатую, локально известную session. Нельзя создавать offline assignment/Start/Complete success без подтверждения сервера. Outbox keyed user+session+operation ID. ACK удаляет pending; 401 требует relogin без утечки предыдущему пользователю; 409 требует сверки, не blind last-write-wins. Logout удаляет доступные другому пользователю кеши; предупреждает о pending unsynced before voluntary logout. Server completion only after sync.

## Human review / assessment
review_task collecting→ready→in_review→published; waiting_for_evidence и needs_update сохраняют связь с предыдущей опубликованной версией. Review version immutable после publication. Private notes отдельная таблица/DTO, не скрытый флаг общего comment. Поздняя версия видео invalidates freshness, не переписывает published вывод. По умолчанию weekly human review только Pro/Pro+; один task на weekly scope. Точное SLA — gate.

Assessment использует program.kind=assessment и обычные training sessions. Протокол/criteria версионируются; criterion outcome passed|not_passed|insufficient_evidence. Readiness ready|not_ready|insufficient_evidence, reason+source evidence обязательны. Нельзя выводить not_ready только потому, что видео недоступно. Реальные thresholds поставляет владелец. Essential assessment рекомендательный; policy для Plus+ explicit, без придуманного строгого gating.

## Billing / AI
Entitlement projection отделена от identity и UI. Trial card required на 7дней Essential/Plus один раз; source webhook/reconcile, не success URL. Отказ/expiry/downgrade прекращает новые запрещённые writes/jobs, но не скрывает собственную историю. Утрата entitlement в середине workout не уничтожает локальный ввод; запись на сервер отклоняется как402, дальнейший доступ требует восстановления, специальный grace не вводится молча.

Analysis states queued→access_check→quality_check→analyzing→succeeded|needs_input|failed|cancelled. Lease/retry durable. Exact video version+fact/rules/protocol/context fingerprint. Observations != decision != program write. Proposal validates allowed type/range/source IDs. Trusted apply всегда заново checks fresh plan/context; old results never applied over owner changes. Private notes доступны AI только по явно разрешённой цели, не все автоматически. Разрешение personalization отдельно от model training. No real processing/Plus-sale until gates.

## AI-розширення — погоджений майбутній контракт 2026-11-24

Деталі й interfaces: [ai-coaching.md](ai-coaching.md). Чинний url attachment
зберігається; S10-10/11 додають private upload intent/finalize, S10-12 —
validated upload_id та optional captured_set_log_id. Один current video
на session_exercise, immutable replacement versions, server owner/revision
checks. Raw video не передається LLM; measurement/interpretation/hypothesis
мають різні поля й обмеження. Report-only не є дозволом processing.

Private storage і PostgreSQL не мають спільної транзакції: lifecycle має
durable intents, generation/lease fencing та bounded cleanup. Нові результати
не публікуються після revoke/delete. Retention звітів і backups визначається
G_PRIVACY. Порівняння перевіряє сумісність method/model/metric/transform/units;
неякісні або несумісні записи не утворюють тренд.

У невиконаних картках номери SQL-файлів не резервують Alembic revision.
Перед DB-карткою інтегратор перевіряє фактичний head та створює наступну
адитивну міграцію; чинні застосовані файли не перейменовуються/не переписуються.
