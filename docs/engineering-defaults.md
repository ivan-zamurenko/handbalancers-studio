# Инженерные defaults v4

Это решения проектирования для старта без лишних уточнений. Они не подменяют продуктовые требования и методику тренера.

| Область | Стартовое решение | Когда пересматривать |
|---|---|---|
| Python | 3.13; patch и lock фиксирует S00-02 | несовместимость/поддержка зависимостей |
| Node | 24, только frontend tests/tooling | несовместимость подтверждённого инструмента |
| Backend I/O | SQLAlchemy 2 sync + psycopg3, sync services/routes; async только там, где обоснован | измеренное contention/потребность |
| Package layout | root pyproject, пакет server/studio; uv.lock | не менять произвольно |
| SQL history | только Alembic для studio/studio_private; managed auth не наш DDL | отдельный ADR |
| Auth | BFF, opaque HttpOnly cookie, encrypted upstream tokens; Supabase owns identity | отдельный threat-model review |
| API | /api без формального /v1 на первом релизе; generate OpenAPI from typed routes | при реальном external client/versioning |
| Theme | auto/light/dark, auto light 07–20 локального устройства | продуктовая корректировка часов |
| Theme during C3 | отложить auto до выхода; ручное сразу | UX review |
| Calendar | date-first, optional scheduled_at; 28-day bounded preview horizon | измеренная потребность |
| Preview | TTL 10 минут, plan/context revisions | UX/latency measurement |
| Idempotency | actor+operation+key, canonical request hash; retention не меньше окна retry, state-specific receipt | реальные сроки provider replay |
| JWT freshness | local revoke мгновенно; upstream user/session validation на входе/refresh и критических действиях; обычные чтения ограничены expiry и кратким freshness TTL | security/UX tradeoff |
| Cookie lifetime | абсолютный 7 дней, idle 24h как conservative app defaults; provider session может истечь раньше | явная конфигурация и тесты |
| Training week | Sunday local 00:00; frozen interval/timezone snapshot | нельзя менять исторические факты |
| Performed-on | фактическая локальная дата начала; progress только после completed | согласованный UX коррекции |
| Timezone change | будущие периоды; текущие и history не пересчитывать | controlled reconciliation |
| Progress target | duration × chosen weekday count snapshot, extra не увеличивает target молча | отдельное изменение плана |
| Date overlap | range intervals UTC half-open [start,end); date-only не выдумывает часы | scheduling UX |
| Offline | запись существующей session, не новый Start/оплата/видео offline | полноценная PWA отдельный scope |
| Worker | долговечный DB job/inbox и ограниченный worker из того же artifact | внешняя очередь только по измеренной нужде |
| Errors | 401 guest, 403 denied capability/CSRF, 404 foreign resource, 402 paid required, 409 revision/idempotency conflict, 422 validation, 429 rate limit, 503 dependency unavailable | контрактные тесты |
| Cursor | сортировка по created_at,id с bounded limit | actual query plan |
| Account expired | свой профиль, completed facts/review доступны; paid writes/new catalog selection закрыты | лицензия доступа к полным платным исходникам G_COMMERCE |
| Correct completed | обычный set-log PUT запрещён; будущая explicit correction отдельная task с audit/data_revision | владелец подтвердит UX |
| Source of truth | versioned catalog, assignments, facts, assessment, adaptation раздельно | не объединять для удобства UI |

Не фиксировать текущий PostgreSQL major по памяти: локальный Supabase и staging должны использовать один совместимый major. Зафиксировать actual `SHOW server_version` и CLI image versions в S01-01; package не выбирает production database plan.

Новые framework/security/API versions проверяются по official docs и lockfile при первой соответствующей задаче. Не обновлять всё окружение в середине работы над другим поведением.
