# Словарь проектных таблиц v3

Сгенерирован из `schema_current.json`. Это логическая целевая модель, не применённая SQL-миграция. Порядок сборки — по рабочим срезам, не все таблицы сразу. Сначала прочитать `MODEL_CURRENT.md`.

## `studio.users`

Продуктовый профиль; Auth остаётся в Supabase.

Этап: 01 · Auth.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `auth_user_id` | `uuid` | нет | unique |
| `first_name` | `text` | нет |  |
| `last_name` | `text` | нет |  |
| `role` | `text` | нет |  |
| `locale` | `text` | нет |  |
| `timezone` | `text` | нет |  |
| `is_active` | `boolean` | нет |  |
| `created_at` | `timestamptz` | нет |  |
| `updated_at` | `timestamptz` | нет |  |
| `row_version` | `integer` | нет |  |

**Ограничения и поведение:** auth_user_id → auth.users.id; role member|coach; locale uk|en; IANA timezone проверяется сервером. UPDATE role недоступен обычному runtime-пути. Email/password не дублируются как источник идентичности.

## `studio.onboarding_profiles`

Текущая анкета, а не объективная оценка.

Этап: 01 · Auth.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `user_id` | `uuid` | нет | pk |
| `goal_codes` | `text[]` | нет |  |
| `self_reported_level` | `smallint` | нет |  |
| `session_minutes` | `smallint` | нет |  |
| `weekdays` | `smallint[]` | нет |  |
| `completed_at` | `timestamptz` | нет |  |
| `updated_at` | `timestamptz` | нет |  |
| `row_version` | `integer` | нет |  |

**Ограничения и поведение:** 1–4 уникальных направления из handstand/strength/mobility/fitness; level 1–3; minutes ∈ {30,45,60,90}; 1–3 уникальных дня в ISO 1–7. Анкета завершена; гостевой draft не создаёт чужой профиль.

## `studio.categories`

Категории упражнений.

Этап: 02 · Каталог.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `code` | `text` | нет | unique |
| `names` | `jsonb` | нет |  |
| `sort_order` | `integer` | нет |  |
| `archived_at` | `timestamptz` | да |  |

**Ограничения и поведение:** names — локализованный небольшой словарь uk/en, а не произвольная доменная БД. Архивация не удаляет связи истории.

## `studio.exercises`

Стабильная идентичность и редактируемый draft упражнения.

Этап: 02 · Каталог.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `created_by_user_id` | `uuid` | нет |  |
| `draft_tracking_kind` | `text` | нет |  |
| `draft_demo_url` | `text` | да |  |
| `archived_at` | `timestamptz` | да |  |
| `created_at` | `timestamptz` | нет |  |
| `updated_at` | `timestamptz` | нет |  |
| `row_version` | `integer` | нет |  |

**Ограничения и поведение:** Корневой ID стабилен. Публикация создаёт exercise_versions. Удаление используемого упражнения запрещено. Member не редактирует общий каталог.

## `studio.exercise_translations`

Редактируемые draft-переводы упражнения.

Этап: 02 · Каталог.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `exercise_id` | `uuid` | нет |  |
| `locale` | `text` | нет |  |
| `title` | `text` | нет |  |
| `instructions` | `text` | нет |  |
| `coaching_cues` | `text` | да |  |

**Ограничения и поведение:** PK(exercise_id,locale); locale uk|en. Published version копирует переводы как immutable snapshot.

## `studio.exercise_categories`

Many-to-many упражнений и категорий.

Этап: 02 · Каталог.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `exercise_id` | `uuid` | нет |  |
| `category_id` | `uuid` | нет |  |

**Ограничения и поведение:** PK(exercise_id,category_id). Каскад разрешён для удаления draft-связи, но не истории выполнения.

## `studio.exercise_versions`

Неизменяемая опубликованная инструкция упражнения.

Этап: 02 · Каталог.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `exercise_id` | `uuid` | нет |  |
| `version_number` | `integer` | нет |  |
| `tracking_kind` | `text` | нет |  |
| `translations_snapshot` | `jsonb` | нет |  |
| `demo_url` | `text` | да |  |
| `metadata_schema_version` | `integer` | нет |  |
| `published_by_user_id` | `uuid` | нет |  |
| `published_at` | `timestamptz` | нет |  |
| `planning_metadata` | `jsonb` | нет |  |

**Ограничения и поведение:** UNIQUE(exercise_id,version_number), UNIQUE(id,exercise_id). tracking_kind reps|duration|reps_load|duration_load. UPDATE/DELETE запрещены обычным продуктовым ролям. planning_metadata — версионируемая typed-разметка владельца; неизвестные характеристики не равны нулевой нагрузке. Не содержит выдуманные физиологические нормы.

## `studio.programs`

Идентичность программы и её владелец.

Этап: 03 · Программы.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `owner_user_id` | `uuid` | нет |  |
| `visibility` | `text` | нет |  |
| `title` | `text` | нет |  |
| `archived_at` | `timestamptz` | да |  |
| `created_at` | `timestamptz` | нет |  |
| `updated_at` | `timestamptz` | нет |  |
| `kind` | `text` | нет |  |

**Ограничения и поведение:** visibility private|catalog (слово shared в v2 означает catalog). owner_user_id обязателен. Каталог публикует coach; member создаёт private. kind training|assessment. Private относится к явному владельцу; каталог не раскрывает персональные копии.

## `studio.program_versions`

Версия и корень транзакционной блокировки дерева программы.

Этап: 03 · Программы.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `program_id` | `uuid` | нет |  |
| `version_number` | `integer` | нет |  |
| `publication_state` | `text` | нет |  |
| `translations_snapshot` | `jsonb` | нет |  |
| `schema_version` | `integer` | нет |  |
| `published_at` | `timestamptz` | да |  |
| `published_by_user_id` | `uuid` | да |  |
| `row_version` | `integer` | нет |  |
| `source_program_version_id` | `uuid` | да |  |
| `created_by_user_id` | `uuid` | да |  |
| `created_actor_type` | `text` | нет |  |
| `origin_analysis_run_id` | `uuid` | да |  |

**Ограничения и поведение:** UNIQUE(program_id,version_number). publication_state draft|published; корень и всё дерево published immutable. source_program_version_id → исходная опубликованная версия. created_actor_type member|coach|ai; member/coach требуют user_id, ai требует analysis_run_id. Публикация AI только доверенной командой; отсутствие published_by_user_id допустимо исключительно для проверенного AI/system-пути. Не использовать вымышленного AI-user.

## `studio.program_workouts`

Шаблон конкретного занятия программы.

Этап: 03 · Программы.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `program_version_id` | `uuid` | нет |  |
| `week_number` | `smallint` | нет |  |
| `position` | `smallint` | нет |  |
| `titles` | `jsonb` | нет |  |
| `planned_minutes` | `smallint` | нет |  |
| `planning_metadata` | `jsonb` | нет |  |
| `standalone_allowed` | `boolean` | нет |  |

**Ограничения и поведение:** UNIQUE(program_version_id,week_number,position), UNIQUE(id,program_version_id). Позиции/неделя > 0; плановая длительность > 0. Это не календарное occurrence. planning_metadata typed и замораживается с версией; standalone_allowed задаёт автор, а не вычисляется из названия занятия.

## `studio.workout_blocks`

Блок шаблонного занятия.

Этап: 03 · Программы.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `program_workout_id` | `uuid` | нет |  |
| `program_version_id` | `uuid` | нет |  |
| `position` | `smallint` | нет |  |
| `block_kind` | `text` | нет |  |
| `title` | `jsonb` | нет |  |

**Ограничения и поведение:** UNIQUE(program_workout_id,position), UNIQUE(id,program_version_id). Composite FK гарантирует принадлежность workout той же program version. MVP: последовательное выполнение; circuits отдельно согласуются.

## `studio.program_exercises`

Предписание упражнения в блоке, не само упражнение.

Этап: 03 · Программы.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `workout_block_id` | `uuid` | нет |  |
| `program_version_id` | `uuid` | нет |  |
| `exercise_id` | `uuid` | нет |  |
| `exercise_version_id` | `uuid` | нет |  |
| `position` | `smallint` | нет |  |
| `side_mode` | `text` | нет |  |
| `notes_snapshot` | `jsonb` | да |  |

**Ограничения и поведение:** UNIQUE(workout_block_id,position), UNIQUE(id,program_version_id). Composite FK exercise_version/exercise_id. Повтор одного exercise_id в разных позициях допустим.

## `studio.program_set_targets`

Одна целевая строка подхода и стороны.

Этап: 03 · Программы.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `program_exercise_id` | `uuid` | нет |  |
| `program_version_id` | `uuid` | нет |  |
| `set_number` | `smallint` | нет |  |
| `side` | `text` | нет |  |
| `tracking_kind` | `text` | нет |  |
| `reps_min` | `integer` | да |  |
| `reps_max` | `integer` | да |  |
| `duration_ms_min` | `bigint` | да |  |
| `duration_ms_max` | `bigint` | да |  |
| `load_kg` | `numeric` | да |  |
| `rest_ms` | `integer` | нет |  |

**Ограничения и поведение:** UNIQUE(program_exercise_id,set_number,side). side bilateral|left|right. CHECK строго по tracking_kind, min≤max, rest≥0; не относящиеся к измерению поля NULL. Стороны не складываются случайно.

## `studio.coach_member_access`

Явное разрешение тренеру работать с персональными данными клиента.

Этап: 04 · Назначения.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `coach_user_id` | `uuid` | нет |  |
| `user_id` | `uuid` | нет |  |
| `status` | `text` | нет |  |
| `source` | `text` | нет |  |
| `granted_at` | `timestamptz` | нет |  |
| `revoked_at` | `timestamptz` | да |  |

**Ограничения и поведение:** Один действующий grant на пару coach/user. source и правовое/договорное основание согласуются. Само наличие роли coach не должно выдавать случайный доступ к любому журналу.

## `studio.user_programs`

Программа, закреплённая за конкретным человеком по фиксированной версии.

Этап: 04 · Назначения.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `user_id` | `uuid` | нет |  |
| `program_version_id` | `uuid` | нет |  |
| `assignment_source` | `text` | нет |  |
| `status` | `text` | нет |  |
| `starts_on` | `date` | нет |  |
| `ends_on` | `date` | да |  |
| `timezone_snapshot` | `text` | нет |  |
| `schedule_snapshot` | `jsonb` | нет |  |
| `replaces_assignment_id` | `uuid` | да |  |
| `created_at` | `timestamptz` | нет |  |
| `row_version` | `integer` | нет |  |
| `training_plan_id` | `uuid` | нет |  |
| `assignment_role` | `text` | нет |  |
| `assigned_by_user_id` | `uuid` | да |  |
| `analysis_run_id` | `uuid` | да |  |

**Ограничения и поведение:** UNIQUE(id,user_id,training_plan_id,program_version_id). Composite FK(plan_id,user_id). Только published version. assignment_role main|assessment; source self|coach|ai. Partial UNIQUE(training_plan_id) WHERE assignment_role='main' AND status IN('active','paused'). Pending не даёт вторую текущую основную; активация всегда транзакционная. Версия назначения immutable: адаптация создаёт successor, старое superseded. Assessment — этап единого плана, не второй независимый календарь. Human source требует assigned_by_user_id; ai требует analysis_run_id.

## `studio.training_weeks`

Границы и цель недели; не счётчик с обнулением истории.

Этап: 04 · Назначения.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `user_id` | `uuid` | нет |  |
| `starts_on` | `date` | нет |  |
| `ends_on` | `date` | нет |  |
| `starts_at` | `timestamptz` | нет |  |
| `ends_at` | `timestamptz` | нет |  |
| `timezone_snapshot` | `text` | нет |  |
| `target_minutes` | `integer` | нет |  |
| `status` | `text` | нет |  |
| `plan_snapshot` | `jsonb` | нет |  |
| `training_plan_id` | `uuid` | нет |  |

**Ограничения и поведение:** UNIQUE(user_id,starts_on), UNIQUE(id,user_id). Воскресенье локального календаря; ends_on=starts_on+7 дней; target≥0. UTC duration может различаться из-за DST. Прошлые цели не пересчитываются из новой анкеты. Week принадлежит единому training_plan того же user. Бюджет недели сохраняется явным snapshot; допзанятие не переписывает прошлую цель молча.

## `studio.scheduled_workouts`

Реальное плановое вхождение шаблонного занятия в календарь.

Этап: 04 · Назначения.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `user_id` | `uuid` | нет |  |
| `program_version_id` | `uuid` | нет |  |
| `program_workout_id` | `uuid` | нет |  |
| `training_week_id` | `uuid` | нет |  |
| `scheduled_for` | `date` | нет |  |
| `status` | `text` | нет |  |
| `skip_reason` | `text` | да |  |
| `replaced_occurrence_id` | `uuid` | да |  |
| `row_version` | `integer` | нет |  |
| `training_plan_id` | `uuid` | нет |  |
| `origin_kind` | `text` | нет |  |
| `user_program_id` | `uuid` | да |  |
| `sequence_number` | `integer` | да |  |
| `scheduled_at` | `timestamptz` | да |  |

**Ограничения и поведение:** UNIQUE(id,user_id,training_plan_id,program_version_id). origin_kind main|additional|assessment. Для main обязательны assignment и sequence_number; additional ссылается на source program_workout/version, но не требует второго назначения. FK occurrence→plan/user и workout→source version; assignment при наличии должен принадлежать plan/user и той же версии. Для assignment-based occurrence UNIQUE(user_program_id,sequence_number), а для отдельных additional повтор защищается idempotency. status planned|in_progress|completed|skipped|missed|cancelled. scheduled_for обязателен; scheduled_at только при выбранном времени. Terminal/начатые occurrence не перепланируются. Источник и статус явно отличимы.

## `studio.training_sessions`

Фактически начатое или вручную внесённое занятие.

Этап: 05 · Тренировка.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `user_id` | `uuid` | нет |  |
| `source` | `text` | нет |  |
| `user_program_id` | `uuid` | да |  |
| `program_version_id` | `uuid` | да |  |
| `scheduled_workout_id` | `uuid` | да |  |
| `status` | `text` | нет |  |
| `completion_kind` | `text` | да |  |
| `started_at` | `timestamptz` | нет |  |
| `completed_at` | `timestamptz` | да |  |
| `performed_on` | `date` | нет |  |
| `timezone_snapshot` | `text` | нет |  |
| `actual_duration_ms` | `bigint` | да |  |
| `manual_minutes` | `integer` | да |  |
| `completion_reason` | `text` | да |  |
| `data_revision` | `integer` | нет |  |
| `row_version` | `integer` | нет |  |
| `created_at` | `timestamptz` | нет |  |
| `training_plan_id` | `uuid` | нет |  |

**Ограничения и поведение:** UNIQUE(id,user_id), UNIQUE(scheduled_workout_id). source guided|manual. Guided требует occurrence и source program_version_id, но user_program_id может быть NULL для additional. Composite FK на occurrence подтверждает plan/user/source version; assignment при наличии согласован с occurrence, а не обязательно с текущим main. Manual не выдумывает prescriptions. Partial UNIQUE(user_id) WHERE status IN('in_progress','paused'). completed требует completion_kind full|partial. Terminal-коррекция отдельная и аудируемая; session snapshots не зависят от будущего main.

## `studio.session_exercises`

Снимок конкретного выполнения упражнения.

Этап: 05 · Тренировка.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `training_session_id` | `uuid` | нет |  |
| `user_id` | `uuid` | нет |  |
| `program_exercise_id` | `uuid` | нет |  |
| `program_version_id` | `uuid` | нет |  |
| `exercise_version_id` | `uuid` | нет |  |
| `position` | `smallint` | нет |  |
| `tracking_kind` | `text` | нет |  |
| `prescription_snapshot` | `jsonb` | нет |  |
| `snapshot_schema_version` | `integer` | нет |  |
| `row_version` | `integer` | нет |  |

**Ограничения и поведение:** UNIQUE(training_session_id,position), UNIQUE(id,user_id). Composite/ancestry checks связывают session, source prescription и version. Snapshot содержит имена, инструкцию, единицы и target IDs. Не зависит от последнего каталога. source program_version относится к конкретному occurrence (включая additional), а не автоматически к текущему main. Snapshot цели неизменяем при перепланировании.

## `studio.set_logs`

Фактический подход.

Этап: 05 · Тренировка.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `session_exercise_id` | `uuid` | нет |  |
| `user_id` | `uuid` | нет |  |
| `target_set_id` | `uuid` | да |  |
| `set_number` | `smallint` | нет |  |
| `side` | `text` | нет |  |
| `status` | `text` | нет |  |
| `tracking_kind` | `text` | нет |  |
| `reps` | `integer` | да |  |
| `duration_ms` | `bigint` | да |  |
| `load_kg` | `numeric` | да |  |
| `skip_reason` | `text` | да |  |
| `recorded_at` | `timestamptz` | нет |  |
| `updated_at` | `timestamptz` | нет |  |
| `row_version` | `integer` | нет |  |

**Ограничения и поведение:** UNIQUE(session_exercise_id,set_number,side). status done|skipped; skipped → фактические значения NULL. done → ровно допустимые метрики tracking_kind. Чужой target запрещён ancestry guard. Дополнительный подход может иметь target_set_id=NULL; он не подменяет выполненность другого target.

## `studio.session_time_segments`

Интервалы реального времени между start/resume и pause/finish.

Этап: 05 · Тренировка.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `training_session_id` | `uuid` | нет |  |
| `started_at` | `timestamptz` | нет |  |
| `ended_at` | `timestamptz` | да |  |
| `source` | `text` | нет |  |

**Ограничения и поведение:** CHECK ended_at≥started_at; partial UNIQUE(training_session_id) WHERE ended_at IS NULL. Не допускаются перекрытия завершённых интервалов; DB exclusion/transaction guard. Source manual_correction отдельно audited.

## `studio.exercise_video_submissions`

Идентичность контрольного подания; один текущий ролик на session exercise.

Этап: 05 · Тренировка.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `session_exercise_id` | `uuid` | нет | unique |
| `user_id` | `uuid` | нет |  |
| `submitted_by_user_id` | `uuid` | нет |  |
| `submitted_at` | `timestamptz` | нет |  |
| `removed_at` | `timestamptz` | да |  |
| `revision` | `integer` | нет |  |

**Ограничения и поведение:** UNIQUE(session_exercise_id). revision указывает на immutable exercise_video_versions(submission_id,version_number); пара принадлежит тому же user. Сменить текущую версию и создать evidence атомарно. После удаления/отзыва доступа не сохранять тайно доступный media payload. Метаданные истории согласно политике, отдельной от исходных байтов.

## `studio.training_reports`

Версионный, детерминированный отчёт о факте.

Этап: 06 · Отчёты/review.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `training_session_id` | `uuid` | нет |  |
| `user_id` | `uuid` | нет |  |
| `version_number` | `integer` | нет |  |
| `source_data_revision` | `integer` | нет |  |
| `algorithm_version` | `text` | нет |  |
| `schema_version` | `integer` | нет |  |
| `payload` | `jsonb` | нет |  |
| `generated_at` | `timestamptz` | нет |  |

**Ограничения и поведение:** UNIQUE(training_session_id,version_number). Published report immutable. Payload — производный snapshot, а не основное место хранения логов. Не содержит private notes и необоснованной оценки техники.

## `studio.review_tasks`

Единица работы тренера: неделя либо отдельное занятие.

Этап: 06 · Отчёты/review.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `user_id` | `uuid` | нет |  |
| `coach_user_id` | `uuid` | нет |  |
| `scope` | `text` | нет |  |
| `training_week_id` | `uuid` | да |  |
| `training_session_id` | `uuid` | да |  |
| `status` | `text` | нет |  |
| `evidence_revision` | `integer` | нет |  |
| `due_at` | `timestamptz` | да |  |
| `created_at` | `timestamptz` | нет |  |
| `row_version` | `integer` | нет |  |

**Ограничения и поведение:** scope weekly|session; ровно соответствующий anchor. UNIQUE(scope,user_id,anchor) реализуется двумя partial indexes. statuses collecting|ready|in_review|waiting_for_evidence|published|needs_update. Weekly human task создаётся по реальному договору, не автоматически всем тарифам.

## `studio.review_task_sessions`

Сессии, включённые в проверку.

Этап: 06 · Отчёты/review.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `review_task_id` | `uuid` | нет |  |
| `training_session_id` | `uuid` | нет |  |
| `user_id` | `uuid` | нет |  |

**Ограничения и поведение:** PK(review_task_id,training_session_id). Все сессии принадлежат тому же user, что task. Не хранить массив сессий без FK в обычном mutable JSON.

## `studio.review_versions`

Черновик/опубликованная версия выводов тренера.

Этап: 06 · Отчёты/review.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `review_task_id` | `uuid` | нет |  |
| `version_number` | `integer` | нет |  |
| `publication_state` | `text` | нет |  |
| `author_user_id` | `uuid` | нет |  |
| `client_summary` | `text` | нет |  |
| `evidence_manifest` | `jsonb` | нет |  |
| `conclusion_code` | `text` | да |  |
| `published_at` | `timestamptz` | да |  |
| `row_version` | `integer` | нет |  |

**Ограничения и поведение:** UNIQUE(review_task_id,version_number). draft можно редактировать; published — immutable вместе с feedback. Evidence manifest фиксирует session/data/video revisions. Late evidence порождает needs_update и новую версию, не изменяет старую.

## `studio.review_feedback`

Видимый клиенту комментарий к конкретному упражнению.

Этап: 06 · Отчёты/review.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `review_version_id` | `uuid` | нет |  |
| `session_exercise_id` | `uuid` | нет |  |
| `user_id` | `uuid` | нет |  |
| `body` | `text` | нет |  |
| `technique_status` | `text` | нет |  |
| `reviewed_video_version_id` | `uuid` | да |  |

**Ограничения и поведение:** FK review/exercise/user и reviewed_video_version_id того же клиента/упражнения. Published parent замораживает feedback. technique_status not_reviewed|reviewed|insufficient_evidence. Private note не входит в эти строки.

## `studio.coach_private_notes`

Приватные рабочие заметки тренера.

Этап: 06 · Отчёты/review.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `user_id` | `uuid` | нет |  |
| `coach_user_id` | `uuid` | нет |  |
| `session_exercise_id` | `uuid` | да |  |
| `body` | `text` | нет |  |
| `created_at` | `timestamptz` | нет |  |
| `updated_at` | `timestamptz` | нет |  |
| `row_version` | `integer` | нет |  |

**Ограничения и поведение:** Отдельная таблица и coach-only DTO. Member API не выполняет SELECT этих полей. Никакой автоматической отправки AI; история правок/удаление — по согласованной политике.

## `studio.assessment_protocols`

Одна версионированная ревизия методики с опубликованной тестовой программой.

Этап: 07 · Оценивание.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `protocol_key` | `text` | нет |  |
| `version_number` | `integer` | нет |  |
| `publication_state` | `text` | нет |  |
| `definition` | `jsonb` | нет |  |
| `schema_version` | `integer` | нет |  |
| `created_by_user_id` | `uuid` | нет |  |
| `published_at` | `timestamptz` | да |  |
| `test_program_version_id` | `uuid` | нет |  |

**Ограничения и поведение:** UNIQUE(protocol_key,version_number). Эта таблица уже содержит ревизии, отдельную assessment_protocol_versions не создавать без причины. FK на published test program version. Draft редактируем, published критерии/definition immutable. Числа и формулы определяет владелец.

## `studio.assessment_runs`

Назначение и решение по одной исходной/повторной оценке.

Этап: 07 · Оценивание.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `user_id` | `uuid` | нет |  |
| `assessment_protocol_id` | `uuid` | нет |  |
| `assessment_kind` | `text` | нет |  |
| `status` | `text` | нет |  |
| `based_on_assessment_id` | `uuid` | да |  |
| `submitted_at` | `timestamptz` | да |  |
| `row_version` | `integer` | нет |  |
| `training_plan_id` | `uuid` | нет |  |
| `assigned_by_user_id` | `uuid` | да |  |

**Ограничения и поведение:** user/plan/protocol version; assessment_kind baseline|reassessment. states assigned|in_progress|submitted|reviewing|published|needs_more_information|cancelled. Факты в обычных sessions. Публикация результатов отдельная. Assigned_by_user_id nullable только для доверенного AI/system-пути с аудитом.

## `studio.assessment_test_runs`

Одна попытка конкретного теста с собственной инструкцией/видео.

Этап: 07 · Оценивание.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `assessment_run_id` | `uuid` | нет |  |
| `test_code` | `text` | нет |  |
| `attempt_number` | `smallint` | нет |  |
| `status` | `text` | нет |  |
| `source_session_exercise_id` | `uuid` | да |  |
| `note` | `text` | да |  |

**Ограничения и поведение:** UNIQUE(assessment_run_id,test_code,attempt_number). Это anchor попытки и source_session_exercise_id, не второй журнал фактов/видео. До начала source может быть NULL; после появления проверяются user и run-session membership. Instructions берутся из опубликованной методики/source snapshot. Независимых youtube_url и копий подходов не создавать.

## `studio.assessment_results`

Версия итогового вывода по тестовой программе; не копия сырых результатов.

Этап: 07 · Оценивание.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `assessment_run_id` | `uuid` | нет |  |
| `user_id` | `uuid` | нет |  |
| `version_number` | `integer` | нет |  |
| `publication_state` | `text` | нет |  |
| `readiness` | `text` | да |  |
| `author_type` | `text` | нет |  |
| `author_user_id` | `uuid` | да |  |
| `analysis_run_id` | `uuid` | да |  |
| `evidence_manifest` | `jsonb` | нет |  |
| `summary` | `text` | нет |  |
| `published_at` | `timestamptz` | да |  |

**Ограничения и поведение:** UNIQUE(assessment_run_id,version_number). publication_state draft|published. readiness ready|not_ready|needs_more_data обязательно при публикации. Author coach|ai: ровно соответствующий author/analysis FK; published immutable. evidence_manifest фиксирует версии фактов, критериев и видео. self_reported_level остаётся в onboarding.

## `studio.billing_customers`

Связь продуктового пользователя со Stripe Customer.

Этап: 08 · Billing.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `user_id` | `uuid` | нет | pk |
| `stripe_customer_id` | `text` | нет | unique |
| `created_at` | `timestamptz` | нет |  |

**Ограничения и поведение:** Создаётся сервером идемпотентно; не по присланному клиентом чужому customer ID.

## `studio.subscriptions`

История и проверенная проекция Stripe Subscription.

Этап: 08 · Billing.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `user_id` | `uuid` | нет |  |
| `stripe_subscription_id` | `text` | нет | unique |
| `stripe_customer_id` | `text` | нет |  |
| `plan_code` | `text` | нет |  |
| `plan_catalog_version` | `integer` | нет |  |
| `currency` | `text` | нет |  |
| `amount_minor` | `integer` | нет |  |
| `status` | `text` | нет |  |
| `current_period_start` | `timestamptz` | нет |  |
| `current_period_end` | `timestamptz` | нет |  |
| `cancel_at_period_end` | `boolean` | нет |  |
| `trial_end` | `timestamptz` | да |  |
| `terms_snapshot` | `jsonb` | нет |  |
| `livemode` | `boolean` | нет |  |
| `synced_at` | `timestamptz` | нет |  |

**Ограничения и поведение:** plan_code essential|plus|pro|pro_plus. Сумма в minor units, не float. Проверенные server mapping/Stripe price. Partial unique для непогашенных конкурентных подписок проектируется по точной state policy. active/trialing не приходит от браузера.

## `studio.checkout_attempts`

Защита от двойного checkout и неизвестного исхода внешнего запроса.

Этап: 08 · Billing.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `user_id` | `uuid` | нет |  |
| `plan_code` | `text` | нет |  |
| `plan_catalog_version` | `integer` | нет |  |
| `idempotency_key` | `text` | нет | unique |
| `request_hash` | `text` | нет |  |
| `state` | `text` | нет |  |
| `stripe_checkout_session_id` | `text` | да |  |
| `stripe_subscription_id` | `text` | да |  |
| `created_at` | `timestamptz` | нет |  |
| `expires_at` | `timestamptz` | да |  |
| `last_error_code` | `text` | да |  |

**Ограничения и поведение:** states reserved|creating|open|awaiting_webhook|completed|expired|failed|unknown. При timeout сначала reconcile; не создавать новую подписку вслепую. Цена/валюта определяются сервером.

## `studio.trial_claims`

Атомарное ограничение одного trial на аккаунт.

Этап: 08 · Billing.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `user_id` | `uuid` | нет | pk |
| `checkout_attempt_id` | `uuid` | нет |  |
| `subscription_id` | `uuid` | да |  |
| `claimed_at` | `timestamptz` | нет |  |
| `state` | `text` | нет |  |

**Ограничения и поведение:** Reservation/consumed/released_after_verified_failure. UNIQUE user защищает одновременный trial. Не отпускать reservation при неизвестном исходе Stripe. Один аккаунт не равно один человек.

## `studio_private.webhook_events`

Долговечный inbox проверенных событий провайдера.

Этап: 08 · Billing.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `provider_event_id` | `text` | нет | pk |
| `provider` | `text` | нет |  |
| `event_type` | `text` | нет |  |
| `object_id` | `text` | нет |  |
| `livemode` | `boolean` | нет |  |
| `provider_created_at` | `timestamptz` | нет |  |
| `received_at` | `timestamptz` | нет |  |
| `status` | `text` | нет |  |
| `attempts` | `integer` | нет |  |
| `next_retry_at` | `timestamptz` | да |  |
| `processed_at` | `timestamptz` | да |  |
| `payload_encrypted` | `text` | да |  |
| `last_error_code` | `text` | да |  |

**Ограничения и поведение:** Сначала подпись, затем insert; event ID уникален. Не гарантирует порядок. Полный payload хранить только при обоснованной необходимости и ограниченном retention; не логировать его в stdout.

## `studio_private.web_sessions`

BFF transport envelope над Supabase Auth session, без собственных паролей.

Этап: 01 · Auth.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `session_key_hash` | `text` | нет | unique |
| `user_id` | `uuid` | нет |  |
| `upstream_session_id` | `uuid` | нет |  |
| `encrypted_tokens` | `text` | нет |  |
| `access_expires_at` | `timestamptz` | нет |  |
| `created_at` | `timestamptz` | нет |  |
| `last_seen_at` | `timestamptz` | нет |  |
| `revoked_at` | `timestamptz` | да |  |
| `row_version` | `integer` | нет |  |

**Ограничения и поведение:** Opaque cookie; ciphertext не ключ шифрования. Lock/CAS при refresh; upstream logout и local revocation тестируются. Клиент не получает refresh token и DB credentials.

## `studio_private.auth_attempts`

Короткоживущая одноразовая попытка PKCE/state и безопасный перенос onboarding.

Этап: 01 · Auth.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `state_hash` | `text` | нет | unique |
| `provider` | `text` | нет |  |
| `encrypted_verifier` | `text` | нет |  |
| `nonce_hash` | `text` | да |  |
| `allowed_return_path` | `text` | нет |  |
| `expires_at` | `timestamptz` | нет |  |
| `consumed_at` | `timestamptz` | да |  |
| `onboarding_draft` | `jsonb` | да |  |

**Ограничения и поведение:** TTL и одноразовое consume в транзакции. Redirect только allowlist. Guest draft переносится лишь при новом signup. Не содержит пароль.

## `studio_private.idempotency_records`

Повтор команды без второго эффекта.

Этап: 04 · Команды.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `actor_user_id` | `uuid` | нет |  |
| `operation` | `text` | нет |  |
| `idempotency_key` | `text` | нет |  |
| `request_hash` | `text` | нет |  |
| `status` | `text` | нет |  |
| `response_resource_id` | `uuid` | да |  |
| `response_code` | `smallint` | да |  |
| `expires_at` | `timestamptz` | нет |  |
| `created_at` | `timestamptz` | нет |  |

**Ограничения и поведение:** UNIQUE(actor_user_id,operation,idempotency_key). Один key с другим body → 409. Owner/auth проверяются до чтения результата. Retention и replay response не заменяют уникальность business rows.

## `studio_private.audit_events`

Минимальный аудит чувствительных переходов и исправлений.

Этап: 04 · Команды.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `actor_user_id` | `uuid` | да |  |
| `action` | `text` | нет |  |
| `entity_type` | `text` | нет |  |
| `entity_id` | `uuid` | нет |  |
| `correlation_id` | `uuid` | нет |  |
| `happened_at` | `timestamptz` | нет |  |
| `redacted_change` | `jsonb` | нет |  |
| `actor_type` | `text` | нет |  |
| `analysis_run_id` | `uuid` | да |  |

**Ограничения и поведение:** Append-only. actor_type member|coach|ai|system; human требует actor_user_id, AI ссылается на реальный analysis_run_id. Polymorphic entity только для журнала, не core ownership. Редактированные изменения без секретов, raw media и полного private note.

## `studio.seed_runs`

Необязательный технический журнал синтетического seed.

Этап: Техническое.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `seed_name` | `text` | нет |  |
| `executed_at` | `timestamptz` | нет |  |
| `metadata` | `jsonb` | нет |  |

**Ограничения и поведение:** Только локальные/разрешённые тестовые данные; не бизнес-сущность. Наличие в старом брифе не делает таблицу обязательной в новой baseline.

## `studio.conversations`

Один приватный канал между клиентом и тренером.

Этап: 09 · Pro+ / после согласования.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `user_id` | `uuid` | нет |  |
| `coach_user_id` | `uuid` | нет |  |
| `status` | `text` | нет |  |
| `member_last_read_at` | `timestamptz` | да |  |
| `coach_last_read_at` | `timestamptz` | да |  |
| `created_at` | `timestamptz` | нет |  |

**Ограничения и поведение:** Только при выборе встроенного чата; иначе согласованный внешний канал не требует этой таблицы. Ограничение доступности/времени ответа отдельно.

## `studio.messages`

Сообщения встроенного чата, не private coach notes.

Этап: 09 · Pro+ / после согласования.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `conversation_id` | `uuid` | нет |  |
| `sender_user_id` | `uuid` | нет |  |
| `body` | `text` | нет |  |
| `sent_at` | `timestamptz` | нет |  |
| `edited_at` | `timestamptz` | да |  |
| `deleted_at` | `timestamptz` | да |  |
| `row_version` | `integer` | нет |  |

**Ограничения и поведение:** Только участники; write entitlement; согласованная политика после окончания подписки. Idempotency при отправке. Не добавлять бинарные attachments без нового решения.

## `studio.coaching_call_periods`

Период предоставления двух 30-минутных звонков.

Этап: 09 · Pro+ / после согласования.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `user_id` | `uuid` | нет |  |
| `subscription_id` | `uuid` | нет |  |
| `starts_at` | `timestamptz` | нет |  |
| `ends_at` | `timestamptz` | нет |  |
| `included_call_count` | `smallint` | нет |  |
| `included_call_minutes` | `smallint` | нет |  |

**Ограничения и поведение:** UNIQUE(subscription_id,starts_at). Начало периода согласуется: billing month либо календарный; не выбирать молча. Значения текущего договора 2 и 30.

## `studio.coaching_calls`

Запрос, подтверждение и факт звонка.

Этап: 09 · Pro+ / после согласования.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `coaching_call_period_id` | `uuid` | нет |  |
| `user_id` | `uuid` | нет |  |
| `coach_user_id` | `uuid` | нет |  |
| `starts_at` | `timestamptz` | да |  |
| `ends_at` | `timestamptz` | да |  |
| `status` | `text` | нет |  |
| `meeting_url` | `text` | да |  |
| `completed_at` | `timestamptz` | да |  |
| `row_version` | `integer` | нет |  |

**Ограничения и поведение:** requested|confirmed|completed|cancelled|no_show. Перенос сохраняет связь истории. Правила no-show/переноса/сгорания кредита ещё не согласованы. Пересечение времени coach запрещается при confirmed.

## `studio.user_preferences`

Предпочтения внешнего вида для каждой роли.

Этап: 01 · Auth.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `user_id` | `uuid` | нет | pk |
| `theme_preference` | `text` | нет |  |
| `revision` | `integer` | нет |  |
| `updated_at` | `timestamptz` | нет |  |

**Ограничения и поведение:** FK user_id. theme_preference auto|light|dark; default auto. Храним выбор, не вычисленную текущую тему. CAS revision.

## `studio.training_plans`

Единый личный план пользователя, общий для клиента и админки.

Этап: 04 · План.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `user_id` | `uuid` | нет |  |
| `management_mode` | `text` | нет |  |
| `status` | `text` | нет |  |
| `planning_rule_set_id` | `uuid` | да |  |
| `coach_user_id` | `uuid` | да |  |
| `row_version` | `integer` | нет |  |
| `created_at` | `timestamptz` | нет |  |
| `archived_at` | `timestamptz` | да |  |

**Ограничения и поведение:** UNIQUE(id,user_id). Partial UNIQUE(user_id) WHERE status IN ('active','paused'). management_mode self|ai|coach; status active|paused|archived. Нулевое основное назначение допустимо до выбора. Любое событие, меняющее планировочный контекст (включая факт нагрузки), инвалидирует старый preview. История archived сохраняется.

## `studio.exercise_video_versions`

Точная ревизия ссылки/evidence для проверки и анализа.

Этап: 05 · Выполнение.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `submission_id` | `uuid` | нет |  |
| `user_id` | `uuid` | нет |  |
| `version_number` | `integer` | нет |  |
| `provider` | `text` | нет |  |
| `provider_asset_id` | `text` | нет |  |
| `canonical_url` | `text` | нет |  |
| `submitted_by_user_id` | `uuid` | нет |  |
| `submitted_at` | `timestamptz` | нет |  |
| `access_status` | `text` | нет |  |

**Ограничения и поведение:** UNIQUE(submission_id,version_number), UNIQUE(id,user_id). Provider youtube|vimeo|google_drive по включённым адаптерам, а не все автоматически. Содержимое версии immutable; access_status может обновляться. Строгая нормализация URL, отсутствие секретов/токенов в canonical_url; доступ контролируется адаптером. Не хранить прямые краткоживущие credentials в публичном JSON.

## `studio.assessment_criteria`

Критерии конкретной версии тестовой методики.

Этап: 07 · Оценка.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `assessment_protocol_id` | `uuid` | нет |  |
| `criterion_code` | `text` | нет |  |
| `program_exercise_id` | `uuid` | нет |  |
| `method` | `text` | нет |  |
| `unit` | `text` | да |  |
| `rubric` | `jsonb` | нет |  |

**Ограничения и поведение:** UNIQUE(assessment_protocol_id,criterion_code). Criterion/exercise должен принадлежать версии тестовой программы протокола. rubric typed/версионированный; отсутствие thresholds не заполняется автоматически. Публикация протокола замораживает дерево.

## `studio.assessment_run_sessions`

Связь тестовой попытки с обычными тренировочными сессиями.

Этап: 07 · Оценка.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `assessment_run_id` | `uuid` | нет |  |
| `training_session_id` | `uuid` | нет |  |
| `user_id` | `uuid` | нет |  |

**Ограничения и поведение:** PK(assessment_run_id,training_session_id). Composite owner integrity; session действительно содержит тестовые source-workouts данного protocol либо явный допустимый anchor.

## `studio.assessment_criterion_results`

Выводы по критериям, составляющие версию оценки.

Этап: 07 · Оценка.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `assessment_result_id` | `uuid` | нет |  |
| `assessment_criterion_id` | `uuid` | нет |  |
| `assessment_test_run_id` | `uuid` | да |  |
| `session_exercise_id` | `uuid` | да |  |
| `user_id` | `uuid` | нет |  |
| `status` | `text` | нет |  |
| `observed_value` | `jsonb` | да |  |
| `reason` | `text` | нет |  |
| `evidence_manifest` | `jsonb` | нет |  |

**Ограничения и поведение:** UNIQUE(assessment_result_id,assessment_criterion_id). Критерий принадлежит протоколу run, все evidence того же user. status meets|does_not_meet|not_assessable|missing|unable_to_perform. observed_value только типизированное наблюдение/производный вывод, raw sets не дублируются. Freeze с assessment_results.

## `studio.planning_rule_sets`

Published правила совместимости и допустимых преобразований.

Этап: 06 · Планировщик.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `rule_set_key` | `text` | нет |  |
| `version_number` | `integer` | нет |  |
| `publication_state` | `text` | нет |  |
| `definition` | `jsonb` | нет |  |
| `schema_version` | `integer` | нет |  |
| `created_by_user_id` | `uuid` | нет |  |
| `published_at` | `timestamptz` | да |  |

**Ограничения и поведение:** UNIQUE(rule_set_key,version_number). draft|published, immutable after publish. Typed rule definition по методике владельца, без выдуманных нормативов. Catalog-политика, применяемая к плану, фиксируется версией.

## `studio.plan_permissions`

Разрешённые действия клиента в конкретном едином плане.

Этап: 06 · Планировщик.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `training_plan_id` | `uuid` | нет | pk |
| `user_id` | `uuid` | нет |  |
| `allow_self_move` | `boolean` | нет |  |
| `allow_listed_replacements` | `boolean` | нет |  |
| `allow_listed_additions` | `boolean` | нет |  |
| `require_request_for_other_changes` | `boolean` | нет |  |
| `row_version` | `integer` | нет |  |
| `updated_by_user_id` | `uuid` | нет |  |
| `updated_at` | `timestamptz` | нет |  |

**Ограничения и поведение:** FK(plan,user). Права не расширяют entitlement. Essential self-policy, Pro/Pro+ owner-policy. Изменение permissions инвалидирует preview. Списки workout options хранятся FK-строками, не произвольным массивом UUID в JSON.

## `studio.permitted_workout_options`

Разрешённые тренером дополнительные занятия/замены.

Этап: 06 · Планировщик.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `training_plan_id` | `uuid` | нет |  |
| `option_kind` | `text` | нет |  |
| `program_workout_id` | `uuid` | нет |  |
| `program_version_id` | `uuid` | нет |  |
| `replaces_program_workout_id` | `uuid` | да |  |

**Ограничения и поведение:** option_kind replacement|additional. FK workout/version; replacement ссылается на заменяемый слот/источник и не означает произвольную эквивалентность. Набор относится к plan. Не обходит правила совместимости; изменения через права тренера.

## `studio.planning_previews`

Серверный предварительный расчёт и журнал применённого набора изменений.

Этап: 06 · Планировщик.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `training_plan_id` | `uuid` | нет |  |
| `user_id` | `uuid` | нет |  |
| `requested_by_user_id` | `uuid` | да |  |
| `operation` | `text` | нет |  |
| `base_plan_revision` | `integer` | нет |  |
| `context_fingerprint` | `text` | нет |  |
| `planning_rule_set_id` | `uuid` | да |  |
| `outcome` | `text` | нет |  |
| `state` | `text` | нет |  |
| `requested_change` | `jsonb` | нет |  |
| `changes` | `jsonb` | нет |  |
| `explanations` | `jsonb` | нет |  |
| `created_at` | `timestamptz` | нет |  |
| `expires_at` | `timestamptz` | нет |  |
| `applied_at` | `timestamptz` | да |  |

**Ограничения и поведение:** state ready|blocked|applied|expired|stale; outcome allowed|conflict|insufficient_data|requires_approval. Apply только allowed/ready после повторной проверки всех зависимостей. changes typed серверный diff, не исполняемый код и не клиентский SQL. Явные UUID в diff перепроверяются по ownership. Applied preview сохраняет before/after; отдельную дублирующую event-таблицу не требуется, audit уже есть.

## `studio.schedule_change_requests`

Желание клиента изменить контролируемый тренером план.

Этап: 06 · Планировщик.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `training_plan_id` | `uuid` | нет |  |
| `user_id` | `uuid` | нет |  |
| `requested_by_user_id` | `uuid` | нет |  |
| `operation` | `text` | нет |  |
| `target_occurrence_id` | `uuid` | да |  |
| `source_program_workout_id` | `uuid` | да |  |
| `source_program_version_id` | `uuid` | да |  |
| `desired_date` | `date` | да |  |
| `expected_plan_revision` | `integer` | нет |  |
| `status` | `text` | нет |  |
| `reason` | `text` | да |  |
| `resolved_by_user_id` | `uuid` | да |  |
| `applied_preview_id` | `uuid` | да |  |
| `created_at` | `timestamptz` | нет |  |
| `resolved_at` | `timestamptz` | да |  |

**Ограничения и поведение:** status pending|applied|rejected|cancelled|stale. Запрос не меняет календарь. Review/approve получает fresh preview и применяет транзакционно. Target того же plan/user, source доступен по тарифу и published. applied требует applied_preview_id.

## `studio.analysis_runs`

Долговечное задание/попытка анализа для конкретного клиента.

Этап: 09 · AI.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `user_id` | `uuid` | нет |  |
| `status` | `text` | нет |  |
| `provider` | `text` | нет |  |
| `model_version` | `text` | нет |  |
| `configuration_version` | `text` | нет |  |
| `assessment_protocol_id` | `uuid` | да |  |
| `input_fingerprint` | `text` | нет |  |
| `attempt` | `integer` | нет |  |
| `created_at` | `timestamptz` | нет |  |
| `finished_at` | `timestamptz` | да |  |
| `error_code` | `text` | да |  |

**Ограничения и поведение:** queued|access_check|quality_check|analyzing|succeeded|needs_input|failed|cancelled. Версия модели и методики фиксируются, metadata не подтверждает качество. Не создавать параллельно analysis_jobs без отдельного назначения. Повторы/ключи и lease уточнить в реализации.

## `studio.analysis_inputs`

Точные версии допустимого evidence одного analysis run.

Этап: 09 · AI.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `analysis_run_id` | `uuid` | нет |  |
| `user_id` | `uuid` | нет |  |
| `video_version_id` | `uuid` | да |  |
| `training_session_id` | `uuid` | да |  |
| `session_data_revision` | `integer` | да |  |
| `context_snapshot` | `jsonb` | нет |  |
| `quality_status` | `text` | нет |  |

**Ограничения и поведение:** Хотя бы один тип evidence/context задан; same-user FK. Snapshot версионирован, не содержит секретов и не заменяет core FK. Permission и актуальность доступа проверяются при выдаче материалa и применении. Отзыв доступа предотвращает новую внешнюю обработку.

## `studio.analysis_observations`

Наблюдение AI по конкретному входу/критерию.

Этап: 09 · AI.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `analysis_run_id` | `uuid` | нет |  |
| `analysis_input_id` | `uuid` | нет |  |
| `assessment_criterion_id` | `uuid` | да |  |
| `start_ms` | `bigint` | да |  |
| `end_ms` | `bigint` | да |  |
| `observability` | `text` | нет |  |
| `observation` | `jsonb` | нет |  |

**Ограничения и поведение:** Input относится к этому run. 0≤start≤end при видео; not_assessable не превращается в плохую технику. observed|not_assessable. Typed observation со ссылкой на методику; никаких медицинских гарантий.

## `studio.adaptation_proposals`

Типизированные изменения будущего плана, отдельно от исполнения.

Этап: 09 · AI.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `user_id` | `uuid` | нет |  |
| `training_plan_id` | `uuid` | нет |  |
| `base_assignment_id` | `uuid` | нет |  |
| `base_program_version_id` | `uuid` | нет |  |
| `expected_plan_revision` | `integer` | нет |  |
| `expected_assignment_revision` | `integer` | нет |  |
| `analysis_run_id` | `uuid` | да |  |
| `review_version_id` | `uuid` | да |  |
| `status` | `text` | нет |  |
| `changes` | `jsonb` | нет |  |
| `reason` | `text` | нет |  |
| `applied_assignment_id` | `uuid` | да |  |
| `created_at` | `timestamptz` | нет |  |
| `applied_at` | `timestamptz` | да |  |

**Ограничения и поведение:** draft|validated|applied|stale|rejected|needs_more_data. Явный источник AI или coach review; все anchor того же пользователя. Apply только доверенная операция после проверки базовых версий и permissions. Одна команда создаёт один successor assignment. Не менять начатое/выполненное и чужой каталог.

## `studio.processing_permissions`

Фиксация согласованных разрешений обработки, не юридический шаблон.

Этап: 08 · Видео.

| Поле | Тип | NULL | Метка |
|---|---|---|---|
| `id` | `uuid` | нет | pk |
| `user_id` | `uuid` | нет |  |
| `purpose` | `text` | нет |  |
| `policy_version` | `text` | нет |  |
| `status` | `text` | нет |  |
| `granted_at` | `timestamptz` | нет |  |
| `revoked_at` | `timestamptz` | да |  |

**Ограничения и поведение:** purpose personalization|model_training; status granted|revoked. Разные цели не подразумевают друг друга. Законные основания/текст/сроки должен утвердить владелец с нужной проверкой. Runtime не создаёт согласие задним числом.
