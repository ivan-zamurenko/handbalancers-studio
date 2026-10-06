# БД: инварианты, на которых строится реализация

## Источник и актуальность
`schema_v4.json` — консолидированный словарь полей. Он включает 62 сущности v3 и техническую auth_rate_limits; это design target, не фактическая БД. `database-introduction.md` привязывает каждую к задаче. Ни один DDL из прежнего проекта не запускать автоматически.

V4-уточнения открыто меняют старую схему: main→primary; pending включён в единственность текущего primary; names NULL для незавершённого verified OAuth профиля; preferences storage row_version; plan context_revision отдельно от row_version; analysis lease/retry fields. Поля auth secret storage допускают доработку конкретного AEAD envelope, но не plaintext.

## Общие технические правила
UUID identity, UTC timestamptz для событий, date+IANA snapshot для расписания/недель. Enum baseline — TEXT+CHECK, чтобы эволюция была явной миграцией без ненужных тяжёлых ENUM conversions. FK индексировать по реальному use/query, unique parent anchors задать явно. NOT NULL где жизненный цикл требует данные, отсутствие не заменять фиктивным значением. Numeric load, integer duration_ms; JSONB только versioned snapshots/rule definitions/report, не замена связям user/plan/source.

Для каждого нового объекта проверить: tenant/owner chain; CHECK state/type; доступ под studio_web, не owner; запреты DELETE/UPDATE исторического факта; два concurrent connections; rollback midway. RLS ownership и SQL privileges дополняют друг друга. Табличные владельцы/BYPASSRLS обходят обычные политики [S-RLS]; production runtime ими быть не должен.

## Обязательные relational anchors
- users UNIQUE(id), UNIQUE(auth_user_id) → managed auth.users.id. Административное назначение coach, не trigger «первый пользователь».
- training_plans UNIQUE(id,user_id); partial UNIQUE(user_id) WHERE status IN('active','paused').
- user_programs UNIQUE(id,user_id,training_plan_id,program_version_id); composite FK(plan,user); current primary unique включает pending/active/paused. Nullable analysis_run_id до AI migration; позднее constraint по source.
- program_workouts UNIQUE(id,program_version_id); child prescription принадлежит именно этому tree. Composite chain blocks/workouts/version, либо typed deferred constraint trigger с transaction lock корня; не просто четыре независимых FK, которые позволяют смешивать деревья.
- scheduled_workouts UNIQUE(id,user_id,training_plan_id,program_version_id); FK на plan/user, workout/version; assignment при наличии той же версии. Для primary/assessment assignment обязателен, для additional допустим NULL. CHECK соответствующих source полей. UNIQUE(user_program_id,sequence_number) для назначенных occurrences; new extras bounded idempotency.
- training_sessions UNIQUE(scheduled_workout_id); composite occurrence/user/plan/version FK; partial UNIQUE(user_id) IN(in_progress,paused); manual без фиктивных targets. Source version snapshot исторический, не join только с текущим назначением.
- session_exercises и set_logs составными связями подтверждают принадлежность session/user/source. UNIQUE(session_exercise_id,set_number,side). Не скрывать nullable side в unique: default 'none', side NOT NULL.
- один активный time segment на session; end>=start; terminal сессия не имеет open segment. При pause/complete закрывать атомарно.
- review_versions version_number unique(task); published immutable. Feedback и private_notes имеют разные output DTO и policies; экспорт клиента не joins notes.
- video logical submission unique(session_exercise); immutable child versions; active version FK указывает на дочерний объект той же submission; soft withdrawal не стирает evidence review.
- current rights/processing consent/rules проверяются повторно в apply, даже если pinned historical source хранится для объяснения.

## SQL не может обычным CHECK проверять соседнюю таблицу
Принадлежность дерева выражать composite FK/UNIQUE, а published status/immutability — транзакционный service guard и DB trigger по нужному anchor. Не писать CHECK с подзапросом. В trigger фиксировать schema-qualified functions, безопасный search_path и ограниченные EXECUTE grants. Все child writes lock published-version root в том же порядке, что publish; иначе race может поменять дерево после проверки.

## RLS и roles
migration_owner: only operator. studio_auth_runtime: narrow token lookup/provision functions, нет общих table SELECT policies «всем». studio_web: нет BYPASSRLS/ownership; SET LOCAL actor из проверенной session, pooled connection не переносит контекст. studio_worker: scoped job/billing privileges. Проверить anonymous, member A/B, coach с relation/без, revoked relation, worker misuse. Подмена произвольного GUC невозможна из браузера; полностью скомпрометированный backend остаётся доверенной границей, RLS не магический sandbox.

## Миграции и data truth
Alembic изменяет только studio/studio_private и необходимые grants/functions. Supabase managed auth не пересоздавать. Один authoritative migration ledger для product. Допустим local-only synthetic seed с seed_runs; миграции schema не создают ложные реальные клиенты. Каталог version immutable, фактические training rows не CASCADE DELETE вслед за archive catalogue. Удаление user/data имеет отдельный разрешённый retention runbook.

Автогенерация Alembic требует ручного просмотра [S-ALEMBIC]. Number в roadmap задаёт слот/порядок, не повод создавать 48 пустых миграций. Если optional S15 не выполняется, следующий реально созданный revision ссылается на фактический head. Интегратор единолично разрешает головы/нумерацию; два writer не генерируют миграции параллельно.

## Незакрытые вещи не выдавать за согласованные
Точные rule thresholds, assessment protocol, consent/retention, channel/provider limits — gates. Они не мешают чистым fake/fixture tests. Таблицы/поля для реального адаптера добавляются маленькой отдельной миграцией после выбранного формата, не мешком optional JSON «на всё».
