# Roadmap v4 — поетапний розвиток Studio

Реєстр містить **167 карток**. Фактичні статуси й evidence — у `.workflow/state.json`; цей індекс не означає готовність функцій.

Початок: `python tools/roadmap.py next`. Залежності визначають порядок; номер Sxx не є жорсткою чергою. Пріоритет власника 2026-11-24: просте поступове AI-ведення в поточному продукті та навчання Python з основ.

Контракти: [AI-супровід і дані](../docs/ai-coaching.md), [навчання](../docs/learning/README.md), [перше завдання](../docs/learning/01-duration.md), [віхи](MILESTONES.md).

Старі номери майбутніх міграцій у невиконаних картках — історичні орієнтири. Не створювати їх наперед і не перезаписувати застосовані файли: наступну revision визначає інтегратор за фактичним Alembic head.

## S00 — Основа пустого репозитория

Запускаемый минимальный FastAPI и воспроизводимые инструменты, без продуктовой логики.

| Задача | Результат | Перевірка |
|---|---|---|
| [S00-01](tasks/S00-01_workspace.md) | Создать изолированный рабочий репозиторий | tooling |
| [S00-02](tasks/S00-02_toolchain.md) | Зафиксировать воспроизводимый toolchain | tooling |
| [S00-03](tasks/S00-03_app_factory.md) | Создать фабрику FastAPI и liveness | contracts |
| [S00-04](tasks/S00-04_settings.md) | Валидировать конфигурацию и скрывать секреты | unit |
| [S00-05](tasks/S00-05_js_harness.md) | Настроить JS и браузерные проверки | tooling |
| [S00-06](tasks/S00-06_error_contract.md) | Ввести единый контракт ошибок и correlation ID | contracts |
| [S00-07](tasks/S00-07_ci_baseline.md) | Проверять каждый небольшой коммит в CI | tooling |
| [S00-08](tasks/S00-08_agent_integrations.md) | Підключити Superpowers і Firecrawl для цього проєкту | tooling |
| [S00-09](tasks/S00-09_ai_coaching_roadmap.md) | Закріпити простий AI-roadmap і навчання власника | tooling |

## S01 — Локальная БД и границы доступа

Изолированный Supabase, Alembic и проверенные права до первых продуктовых записей.

| Задача | Результат | Перевірка |
|---|---|---|
| [S01-01](tasks/S01-01_local_supabase.md) | Поднять одноразовый стенд Supabase для интеграций | tooling |
| [S01-02](tasks/S01-02_migration_baseline.md) | Создать схемы и роли минимальной baseline | integration |
| [S01-03](tasks/S01-03_transaction_context.md) | Передавать actor на время одной транзакции | integration |
| [S01-04](tasks/S01-04_profile_schema.md) | Создать минимальный продуктовый профиль | integration |
| [S01-05](tasks/S01-05_profile_rls.md) | Закрыть профиль и выдачу роли на уровне БД | security |
| [S01-06](tasks/S01-06_auth_storage.md) | Создать server-side хранилище сессий и OAuth attempts | integration |
| [S01-07](tasks/S01-07_migration_ci.md) | Проверить последовательность миграций в CI | tooling |

## S02 — Общая оболочка интерфейса

C1/A1/C3 foundations, UA/EN, доступные формы и обе темы.

| Задача | Результат | Перевірка |
|---|---|---|
| [S02-01](tasks/S02-01_design_tokens.md) | Перенести утверждённые токены без demo-логики | js |
| [S02-02](tasks/S02-02_form_primitives.md) | Создать доступные примитивы формы и диалога | e2e |
| [S02-03](tasks/S02-03_theme_clock.md) | Реализовать auto/light/dark без потери ввода | js |
| [S02-04](tasks/S02-04_localization.md) | Создать UK/EN словари и форматирование | unit |
| [S02-05](tasks/S02-05_http_client.md) | Создать единый браузерный клиент API | js |

## S03 — Регистрация и сессии

Email/password через Supabase, подтверждение, вход, refresh, logout и recovery.

| Задача | Результат | Перевірка |
|---|---|---|
| [S03-01](tasks/S03-01_auth_gateway.md) | Определить Supabase Auth boundary | unit |
| [S03-02](tasks/S03-02_jwt_validation.md) | Проверять Supabase JWT, а не просто декодировать | security |
| [S03-03](tasks/S03-03_signup_request.md) | Принять регистрацию email/password | contracts |
| [S03-04](tasks/S03-04_verify_email.md) | Подтвердить код и создать профиль ровно один раз | integration |
| [S03-05](tasks/S03-05_password_login.md) | Создать вход и защищённую cookie | contracts |
| [S03-06](tasks/S03-06_refresh_session.md) | Сериализовать refresh без гонки токенов | integration |
| [S03-07](tasks/S03-07_logout.md) | Сделать локальный выход немедленным | security |
| [S03-08](tasks/S03-08_password_recovery.md) | Восстановить пароль через ограниченный recovery flow | contracts |
| [S03-09](tasks/S03-09_csrf_rate_limits.md) | Защитить изменяющие запросы и формы входа | security |
| [S03-10](tasks/S03-10_registration_ui.md) | Собрать формы регистрации, кода и входа | e2e |
| [S03-11](tasks/S03-11_auth_local_e2e.md) | Проверить полный путь на настоящем local Supabase | integration |
| [S03-10a](tasks/S03-10a_login_preview.md) | Форма входу для локального перегляду | e2e |
| [S03-10b](tasks/S03-10b_login_layout.md) | Вирівняти допоміжні дії форми входу | e2e |
| [S03-10c](tasks/S03-10c_password_eye.md) | Анімоване око в полі пароля | e2e |

## S04 — Google і профіль власника (Apple виключено)

OAuth через Supabase, связность identities и безопасная выдача роли coach.

| Задача | Результат | Перевірка |
|---|---|---|
| [S04-01](tasks/S04-01_oauth_attempt.md) | Подготовить Google OAuth через Supabase PKCE | security |
| [S04-02](tasks/S04-02_oauth_callback.md) | Обменять OAuth code и восстановить пользовательский путь | contracts |
| [S04-03](tasks/S04-03_apple_adapter.md) | Добавить Apple без предположения о полном имени (skipped: Apple видалено) | contracts |
| [S04-04](tasks/S04-04_identity_linking.md) | Проверить linking и конфликты identities | security |
| [S04-05](tasks/S04-05_coach_bootstrap.md) | Выдать владельцу coach вне публичной регистрации | security |
| [S04-06](tasks/S04-06_profile_preferences.md) | Сохранить профиль и выбор темы на сервере | contracts |
| [S04-01a](tasks/S04-01a_oauth_runtime.md) | Серверний OAuth PKCE для Google та Apple | integration |
| [S04-03a](tasks/S04-03a_oauth_ui.md) | Кнопки Google/Apple і стани OAuth | e2e |
| [S04-02a](tasks/S04-02a_oauth_profile_data.md) | Автоматичний імпорт даних OAuth профілю | integration |

## S05 — Онбординг и права тарифов

Правильный публичный путь и серверная модель доступа без настоящих списаний.

| Задача | Результат | Перевірка |
|---|---|---|
| [S05-01](tasks/S05-01_onboarding_model.md) | Сохранить анкету без медицинского scoring | integration |
| [S05-02](tasks/S05-02_guest_onboarding.md) | Перенести гостевую анкету через вход | e2e |
| [S05-03](tasks/S05-03_public_pages.md) | Восстановить утверждённый публичный путь и тарифы | e2e |
| [S05-04](tasks/S05-04_entitlement_projection.md) | Ввести серверную модель тарифного доступа до Stripe | integration |
| [S05-05](tasks/S05-05_server_guards.md) | Применить единые auth/role/paid guards | security |
| [S05-06](tasks/S05-06_coach_access.md) | Ограничить тренерский доступ к клиенту | integration |
| [S05-07](tasks/S05-07_command_receipts.md) | Ввести идемпотентные команды для продуктовых эффектов | integration |
| [S05-03a](tasks/S05-03a_public_preview.md) | Запустити незалежний публічний лендінг для перегляду | e2e |
| [S05-03b](tasks/S05-03b_landing_refinement.md) | Уточнити схему поступу та іконки спорядження | e2e |

## S06 — Упражнения

Создание, публикация и неизменяемые ревизии с тренерским интерфейсом.

| Задача | Результат | Перевірка |
|---|---|---|
| [S06-01](tasks/S06-01_exercise_drafts.md) | Создать упражнение и переводы как черновик | integration |
| [S06-02](tasks/S06-02_measurement_types.md) | Зафиксировать типы фактического результата | unit |
| [S06-03](tasks/S06-03_exercise_publish.md) | Публиковать неизменяемую ревизию упражнения | integration |
| [S06-04](tasks/S06-04_exercise_browse.md) | Дать поиск и просмотр доступного каталога | contracts |
| [S06-05](tasks/S06-05_exercise_editor_ui.md) | Собрать тренерский редактор упражнения | e2e |
| [S06-07](tasks/S06-07_exercise_demonstration.md) | Прив’язати приклад виконання до версії вправи | integration |
| [S06-06](tasks/S06-06_planning_metadata.md) | Описать нагрузку без выдуманных нормативов | unit |

## S07 — Программы

Общий конструктор coach/member, дерево программы и публикация.

| Задача | Результат | Перевірка |
|---|---|---|
| [S07-01](tasks/S07-01_program_identity.md) | Создать private/catalog программу и первый draft | integration |
| [S07-02](tasks/S07-02_workout_structure.md) | Добавить и упорядочить занятия внутри draft | integration |
| [S07-03](tasks/S07-03_block_structure.md) | Добавить блоки занятия | integration |
| [S07-04](tasks/S07-04_prescriptions.md) | Назначить конкретную ревизию упражнения | integration |
| [S07-05](tasks/S07-05_set_targets.md) | Задать целевые подходы | integration |
| [S07-06](tasks/S07-06_publish_tree.md) | Опубликовать и заморозить всё дерево программы | integration |
| [S07-07](tasks/S07-07_clone_derivative.md) | Создать новый draft или персональную производную | integration |
| [S07-08](tasks/S07-08_program_catalog.md) | Показать общий и собственный каталог без paywall по количеству | contracts |
| [S07-09](tasks/S07-09_builder_ui.md) | Собрать общий конструктор для клиента и тренера | e2e |

## S08 — Основная программа и единый календарь

Один личный план, основное назначение и реальные занятия.

| Задача | Результат | Перевірка |
|---|---|---|
| [S08-01](tasks/S08-01_single_plan.md) | Создать один текущий личный план | integration |
| [S08-02](tasks/S08-02_primary_assignment.md) | Назначить одну основную published программу | integration |
| [S08-03](tasks/S08-03_training_weeks.md) | Зафиксировать локальные недели и плановые минуты | integration |
| [S08-04](tasks/S08-04_scheduled_occurrences.md) | Материализовать реальные занятия единого календаря | integration |
| [S08-05](tasks/S08-05_coach_assignment_ui.md) | Назначить программу из админки | e2e |
| [S08-06](tasks/S08-06_client_today.md) | Собрать C1 по реальным данным | e2e |

## S09 — Фактическая тренировка

C3, подходы, паузы, сохранение, завершение и история.

| Задача | Результат | Перевірка |
|---|---|---|
| [S09-01](tasks/S09-01_session_start.md) | Начать занятие один раз и сделать snapshot | integration |
| [S09-02](tasks/S09-02_record_sets.md) | Сохранить факт подхода с optimistic concurrency | integration |
| [S09-03](tasks/S09-03_session_timing.md) | Сохранить паузу, продолжение и активные сегменты | integration |
| [S09-04](tasks/S09-04_complete_session.md) | Завершить занятие и сформировать фактический отчёт атомарно | integration |
| [S09-05](tasks/S09-05_abandon_session.md) | Прекратить начатую тренировку без ложного завершения | integration |
| [S09-06](tasks/S09-06_manual_session.md) | Добавить ручную запись выполненного занятия | integration |
| [S09-07](tasks/S09-07_workout_c3.md) | Собрать активную тренировку C3 | e2e |
| [S09-08](tasks/S09-08_offline_outbox.md) | Сохранить ввод при временной потере сети | js |
| [S09-09](tasks/S09-09_progress_history.md) | Показать историю и недельный факт без двойного счёта | integration |
| [S09-10](tasks/S09-10_training_roundtrip.md) | Пройти первый тренировочный вертикальный срез | e2e |

## S10 — Видео и проверка тренера

Версии evidence, A1, черновик и публикация feedback.

| Задача | Результат | Перевірка |
|---|---|---|
| [S10-01](tasks/S10-01_media_links.md) | Распознать видеоссылки без скачивания | unit |
| [S10-02](tasks/S10-02_media_versions.md) | Хранить один текущий ролик с историей замен | integration |
| [S10-03](tasks/S10-03_weekly_review_tasks.md) | Создать одну задачу личной проверки за неделю | integration |
| [S10-04](tasks/S10-04_private_notes.md) | Отделить приватную заметку от клиентского feedback | security |
| [S10-05](tasks/S10-05_review_draft.md) | Создать черновик проверки с точным evidence | integration |
| [S10-06](tasks/S10-06_review_publish.md) | Опубликовать вывод отдельно от изменения плана | integration |
| [S10-07](tasks/S10-07_late_evidence.md) | Пометить проверку при позднем видео | integration |
| [S10-08](tasks/S10-08_coach_a1.md) | Собрать A1: клиент, факты, проверка | e2e |
| [S10-09](tasks/S10-09_member_feedback.md) | Показать проверку и фактический отчёт клиенту | e2e |
| [S10-10](tasks/S10-10_private_upload_intent.md) | Видати обмежений дозвіл приватного завантаження | integration |
| [S10-11](tasks/S10-11_upload_finalize.md) | Перевірити файл і надійно завершити upload | integration |
| [S10-12](tasks/S10-12_capture_set_binding.md) | Зв’язати відеоверсію з обраним підходом | integration |
| [S10-13](tasks/S10-13_exercise_video_upload_ui.md) | Додати відео одного підходу в C3 | e2e |
| [S10-14](tasks/S10-14_media_lifecycle.md) | Видаляти приватне медіа та його похідні | integration |

## S11 — Планировщик и самостоятельный выбор

Правила, preview/apply, Essential и разрешения Pro/Pro+.

| Задача | Результат | Перевірка |
|---|---|---|
| [S11-01](tasks/S11-01_rules_versioning.md) | Создать версии правил владельца | integration |
| [S11-02](tasks/S11-02_compatibility_engine.md) | Проверить совместимость единого плана | unit |
| [S11-03](tasks/S11-03_availability_candidates.md) | Найти доступные даты с минимальными изменениями | unit |
| [S11-04](tasks/S11-04_planning_preview.md) | Сохранить серверный preview изменений | integration |
| [S11-05](tasks/S11-05_planning_apply.md) | Применить только актуальный preview атомарно | integration |
| [S11-06](tasks/S11-06_essential_main_change.md) | Дать Essential заменить основную программу | e2e |
| [S11-07](tasks/S11-07_essential_add_replace.md) | Дать клиенту выбрать отдельное занятие | e2e |
| [S11-08](tasks/S11-08_move_and_skip.md) | Перенести или пропустить занятие без бесконечного долга | integration |
| [S11-09](tasks/S11-09_coach_permissions.md) | Настроить границы самостоятельных изменений Pro | integration |
| [S11-10](tasks/S11-10_change_requests.md) | Создать запрос клиента без изменения календаря | integration |
| [S11-11](tasks/S11-11_approve_request.md) | Одобрить запрос через свежий расчёт | integration |
| [S11-12](tasks/S11-12_planner_properties.md) | Проверить конкуренцию и инварианты планировщика | integration |

## S12 — Тестовая программа и оценка

Методика владельца и оценка через тот же тренировочный движок.

| Задача | Результат | Перевірка |
|---|---|---|
| [S12-01](tasks/S12-01_assessment_protocol.md) | Создать версионируемую методику тестовой программы | integration |
| [S12-02](tasks/S12-02_assessment_assignment.md) | Назначить тест в тот же личный план | integration |
| [S12-03](tasks/S12-03_criterion_results.md) | Записать наблюдения отдельно от фактического результата | integration |
| [S12-04](tasks/S12-04_readiness_publish.md) | Опубликовать решение о следующем этапе | integration |
| [S12-05](tasks/S12-05_assessment_ui.md) | Собрать тестовую программу и переоценку в обоих кабинетах | e2e |

## S13 — Stripe и жизненный цикл доступа

Настоящий test-mode Checkout, события, trial, portal и смена тарифа.

| Задача | Результат | Перевірка |
|---|---|---|
| [S13-01](tasks/S13-01_stripe_gateway.md) | Создать Stripe boundary с серверным каталогом цен | unit |
| [S13-02](tasks/S13-02_checkout_attempts.md) | Создать долговечную попытку Checkout | integration |
| [S13-03](tasks/S13-03_webhook_inbox.md) | Принять подписанное Stripe событие в долговечный inbox | integration |
| [S13-04](tasks/S13-04_subscription_projection.md) | Обновлять подписку идемпотентно и вне порядка событий | integration |
| [S13-05](tasks/S13-05_trial_claims.md) | Выдать один trial на аккаунт | integration |
| [S13-06](tasks/S13-06_billing_portal.md) | Дать управление оплатой через Stripe Portal | contracts |
| [S13-07](tasks/S13-07_tier_transitions.md) | Согласовать смену тарифа с управлением планом | integration |
| [S13-08](tasks/S13-08_billing_ui_flow.md) | Связать public путь, Checkout ожидание и кабинет | e2e |
| [S13-08a](tasks/S13-08a_prevent_duplicate_subscription.md) | Блокувати дубль підписки при запізнілому webhook | integration |
| [S13-09a](tasks/S13-09a_stripe_endive_card_filter.md) | Stripe Endive card-only Checkout | integration |
| [S13-10](tasks/S13-10_payment_history.md) | Окрема незмінна історія платежів і повернень | integration |
| [S13-09](tasks/S13-09_billing_testmode.md) | Проверить реальную test-mode интеграцию отдельно от mocks | gate |

## S14 — Контролируемая AI-подсистема

Поступове AI-ведення: приватне відео вправи, явні метрики, затверджені знання, звіт і захищена адаптація. Default off.

| Задача | Результат | Перевірка |
|---|---|---|
| [S14-00](tasks/S14-00_handstand_feasibility.md) | Перевірити мінімальний CV/AI стек на дозволених прикладах | tooling |
| [S14-01](tasks/S14-01_processing_permissions.md) | Разделить разрешения персонализации и обучения модели | integration |
| [S14-02](tasks/S14-02_media_access_boundary.md) | Описать доступ к evidence без выбора провайдера за владельца | unit |
| [S14-03](tasks/S14-03_analysis_jobs.md) | Создать долговечные analysis jobs в БД | integration |
| [S14-04](tasks/S14-04_evidence_manifest.md) | Зафиксировать точный контекст анализа | unit |
| [S14-05](tasks/S14-05_observations_schema.md) | Валидировать структурированный результат AI | integration |
| [S14-06](tasks/S14-06_adaptation_draft.md) | Создать проверяемое предложение адаптации | integration |
| [S14-07](tasks/S14-07_ai_evaluation.md) | Создать процедуру проверки качества и shadow mode | tooling |
| [S14-08](tasks/S14-08_guarded_auto_apply.md) | Применить допустимую Plus адаптацию через общий command layer | integration |
| [S14-09](tasks/S14-09_analysis_status_ui.md) | Показать честный статус анализа и объяснение адаптации | e2e |
| [S14-10](tasks/S14-10_handstand_method.md) | Описати версійну методику стійки збоку | integration |
| [S14-11](tasks/S14-11_pose_contract.md) | Визначити змінний pose adapter | unit |
| [S14-12](tasks/S14-12_pose_adapter.md) | Підключити перший перевірений pose adapter | integration |
| [S14-13](tasks/S14-13_pose_quality.md) | Відхиляти непридатний запис і недостатні орієнтири | unit |
| [S14-14](tasks/S14-14_biomechanics_metrics.md) | Обчислювати явні метрики біомеханіки | unit |
| [S14-15](tasks/S14-15_approved_knowledge.md) | Опублікувати вузьку базу перевірених знань | integration |
| [S14-16](tasks/S14-16_knowledge_retrieval.md) | Вибирати затверджені знання простим SQL-пошуком | integration |
| [S14-17](tasks/S14-17_grounded_explanations.md) | Пояснювати факти й відокремлювати гіпотези | integration |
| [S14-18](tasks/S14-18_catalog_recommendations.md) | Добирати рекомендації лише з каталогу | integration |
| [S14-19](tasks/S14-19_analysis_report.md) | Показати версійний звіт і скелет у Studio | e2e |
| [S14-20](tasks/S14-20_analysis_comparison.md) | Порівнювати лише сумісні аналізи | integration |
| [S14-21](tasks/S14-21_coaching_adaptation.md) | Передати рекомендації в чинний планувальник | integration |
| [S14-22](tasks/S14-22_coaching_rollout.md) | Керувати поступовим увімкненням AI | integration |

## S15 — Опциональный Pro+

Реализация согласованного канала общения и учёта двух звонков; не выбирать сервис молча.

| Задача | Результат | Перевірка |
|---|---|---|
| [S15-01](tasks/S15-01_proplus_service_contract.md) | Зафиксировать реальный канал Pro+ до разработки интеграции | gate |
| [S15-02](tasks/S15-02_call_allowance.md) | Учесть две 30-минутные сессии в периоде Pro+ | integration |
| [S15-03](tasks/S15-03_chat_delivery.md) | Реализовать выбранный канал и управление услугой | integration |

## S16 — Укрепление и эксплуатация

Приватность, доступность, наблюдаемость, контейнеры и восстановление.

| Задача | Результат | Перевірка |
|---|---|---|
| [S16-01](tasks/S16-01_accessibility_i18n.md) | Проверить доступность и UA/EN на основных путях | e2e |
| [S16-02](tasks/S16-02_security_regressions.md) | Проверить сквозные security границы | security |
| [S16-03](tasks/S16-03_observability.md) | Добавить полезные метрики и логи без лишних персональных данных | contracts |
| [S16-04](tasks/S16-04_privacy_lifecycle.md) | Спроектировать экспорт/удаление с явными retention правилами | security |
| [S16-05](tasks/S16-05_load_and_indexes.md) | Измерить реальные узкие места перед оптимизацией | tooling |
| [S16-06](tasks/S16-06_container_build.md) | Собрать воспроизводимый локальный контейнер | tooling |
| [S16-07](tasks/S16-07_backup_restore.md) | Проверить восстановление в отдельной среде | gate |
| [S16-08](tasks/S16-08_release_matrix.md) | Собрать матрицу фактической готовности возможностей | tooling |

## S17 — Проверки внешних сервисов и выпуск

Отдельные допуски по SMTP, OAuth, видео, AI и продаваемым тарифам.

| Задача | Результат | Перевірка |
|---|---|---|
| [S17-01](tasks/S17-01_smtp_oauth_live.md) | Проверить внешний email и Google на staging | gate |
| [S17-02](tasks/S17-02_video_access_live.md) | Проверить выбранный путь частного видео | gate |
| [S17-03](tasks/S17-03_ai_release_evaluation.md) | Проверить реальный AI и разрешить ограниченный rollout | gate |
| [S17-04](tasks/S17-04_commerce_ready.md) | Проверить готовность реальной коммерции | gate |
| [S17-05](tasks/S17-05_production_release.md) | Выпустить только утверждённый релиз с rollback планом | gate |
