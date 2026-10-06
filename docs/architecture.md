# Архитектура нового приложения

## Внешняя граница
Браузер → HTTPS → FastAPI → SQLAlchemy → PostgreSQL/Supabase. Jinja отдаёт HTML-shell, ES modules управляют небольшими interactions. Браузер не пишет в studio через Supabase Data API, не получает DB/service-role keys и не определяет tier/role.

Supabase Auth — upstream identity/password/provider sessions. Stripe — external billing truth. Видео/AI — отдельные adapter interfaces, пока реальные providers не выбраны. Один кодовый artifact, один монолит; worker запускает задачи из того же приложения и БД. Это не гарантия process fault isolation.

## Слои без лишних абстракций
`routes.py` — HTTP parsing/auth dependencies/response mapping. `schemas.py` — input/output Pydantic DTO. `service.py` или именованные use-case файлы — transaction orchestration/authorization. Pure policy/calculators — business rules без HTTP/ORM side effects. `models.py` — SQLAlchemy mapping. `queries.py` — read projections. Внешний gateway имеет Protocol только там, где нужна реальная замена/тестирование. Не создавать generic BaseRepository/BaseService на каждый класс.

Внутри модуля service использует SQLAlchemy Session напрямую, пока generic repository не решает реальную проблему. Read-query может собирать view через несколько таблиц, но write ownership остаётся у владеющего модуля. Межмодульный orchestration вызывает публичные сервисные функции, не делает UPDATE чужих tables из route.

## Владельцы модулей
| Модуль | Ответственность | Не его ответственность |
|---|---|---|
| auth | identity, sessions, CSRF, OAuth | тарифы, catalogue writes |
| accounts | product profile, onboarding, preferences, coach access | password hashes |
| billing | subscriptions, trials, entitlement projection | хранение карточных данных |
| catalog | exercises, revisions, categories | session result |
| programs | draft/published program tree, derivative | calendar mutation |
| planning | unified plan, primary assignment, weeks, occurrences, rules, previews/requests | оценка техники видео |
| training | snapshots, set logs, timing, Complete, factual reports | автоматическая смена программы |
| progress | derived own read metrics/history | counters как независимая truth |
| media | video link versions, access capability | самовольный download/publicity |
| reviews | human draft/published feedback, private notes | AI от имени coach |
| assessments | protocols, criteria, readiness/evidence | второй журнал set logs |
| analysis | jobs, observations, proposals, evaluation | произвольный SQL/authority |
| coaching | выбранные Pro+ calls/chat | новая командная SaaS |
| jobs | scheduling execution/retry/lease | отдельная бизнес-истина |
| shared | context/errors/audit/idempotency/clock/IDs | свалка доменной логики |

## Команды и транзакции
Одна request command создаёт один transaction boundary. Lock order: plan → assignment → occurrences → session → logs. Каталог: root program_version → child. Вся branch, меняющая контекст planner, поднимает context_revision под этим же порядком. Изменение schedule поднимает row_version плана. Apply перепроверяет оба.

Идемпотентность — не просто `if exists`: unique command receipt + request hash + transactional effect. Повтор с другим payload — 409. Concurrency не делегируется browser disabled button. Для одного occurrence повтор Start возвращает тот же session; terminal session не воскрешается.

Network-before/after: сохранить durable intent, выполнить bounded upstream call без долгого DB lock, проверить актуальность и записать исход. При неопределённом timeout повторяется тот же upstream key или reconcile, а не создаётся новая оплата/AI операция. Внешнее exactly-once не обещать.

## Доверие и RLS
`migration_owner` — только миграции/operator. `studio_web` — ограниченный runtime без owner/BYPASSRLS. `studio_auth_runtime` — только session lookup/token store и узкое profile provisioning; не доступ ко всем продуктовым таблицам. `studio_worker` — минимальные job/billing операции; AI не имеет его credentials. Использовать несколько маленьких DB pools с общим budget.

Actor context вычислен из проверенной сессии и current role; `SET LOCAL` scope. RLS — дополнительная защита от обычных ошибок доступа, не замена корректного backend и parameterized SQL. Скомпрометированный процесс с правом ставить actor context остаётся внутри доверенной границы.

Самостоятельный frontend role/tier selector разрешён только в references/design preview, не production. Local synthetic seed не создаёт публичный bypass paid access.

## Устойчивость
Clock и ID generation inject для детерминированных тестов. Private response no-store. Retry ограничен с backoff/jitter по внешнему провайдеру; бизнес-ошибка не ретраится. Job errors и request ID доступны оператору без приватных payloads. Append-only audit хранит redacted changes, а не копию секретов.

Увеличение нагрузки сначала измеряется (S16), затем pool/index/query/worker capacity; микросервисы/Redis не добавляются заранее.
