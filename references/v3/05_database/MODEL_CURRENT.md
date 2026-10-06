# База данных — консолидированная проектная модель v3

## Статус и источники
`schema_current.json` и `FIELD_DICTIONARY.md` — новый собранный словарь на основе v1, v2 и последнего утверждения единого плана.
Это **не SQL и не готовые миграции**. PK/FK/CHECK/UNIQUE/RLS/triggers должны быть реализованы и проверены на локальной baseline.
В `relationship_overview` простые связи для чтения; он не утверждает наличие всех обязательных составных ограничений.
Число проектных сущностей не означает, что их нужно создать в первой итерации.
Старые `schema_dictionary.json`/DBML внутри архивов — история, не текущая схема.
`historical_existing_by_brief` — только сведения старого брифа, не новая инспекция remote.

## 1. Основные уровни
`programs` — идентичность общей/private программы.
`program_versions` — draft/immutable published дерево с source_program_version_id.
`training_plans` — единый личный план, общий для UI клиента и тренера.
`user_programs` — привязка версии программы как основной или тестового этапа.
`scheduled_workouts` — реальные записи календаря, включая additional другого источника.
`training_sessions`/`session_exercises`/`set_logs` — фактическое выполнение.
`review_*`/`assessment_*` — выводы, а не подмена фактов.
`analysis_*`/`adaptation_proposals` — evidence и изменения будущего.

## 2. Инвариант одной основной программы
Partial UNIQUE на user_id текущего training_plan (active/paused).
Внутри него не более одного active/paused user_program с assignment_role=main.
Pending не даёт второе текущее назначение; активация проверяет конкурентный переход.
План может временно не иметь основной программы: новый аккаунт, выбор, завершение.
Тестовый этап не создаёт независимый календарь. Additional occurrence не создаёт вторую main assignment.

## 3. Критически важная поправка к старой модели
В v1 каждая guided session требовала assignment/version.
Теперь дополнительное занятие может происходить из другой общей программы без её назначения целиком.
Поэтому source program_workout/version принадлежат occurrence; nullable user_program_id корректен для additional.
Нельзя проверять все session_exercises против текущей основной версии: это сломает дополнительные и исторические занятия.
При этом пользователь и единый план обязательны и защищены составными связями.

## 4. Составные ограничения, не заменяемые одним FK на id
- plan/user у assignments, occurrence и sessions совпадают.
- main/assessment occurrence связан с assignment того же plan/user/source version.
- additional occurrence указывает на доступный published workout нужной source version без фиктивного main.
- session соответствует occurrence по user, plan и source version; session_exercise соответствует source tree.
- set_log принадлежит session exercise того же user; target при наличии соответствует snapshot/source.
- video submission/version принадлежат session exercise/user; review и analysis не подключают чужой evidence.
- criterion принадлежит именно протоколу assessment_run; test session и результаты одного клиента.
- proposal, base assignment, applied assignment и analysis/review относятся к одному plan/user.
Для каждого правила определить composite FK/unique anchor или trigger с тестом. Application-only happy path недостаточен.

## 5. Версии и замены
Изменение published content создаёт новую version. Нельзя менять детей старого дерева.
Персональная адаптация создаёт private derivative и successor assignment; старое назначение становится superseded.
Старая completed/started session сохраняет первоначальный источник и snapshots.
Review/assessment результатов тоже версионируются; новый evidence не переписывает старый вывод.

## 6. Единый календарь
planning_rule_sets — версионируемое definition правил владельца, а не неизвестный AI-score.
plan_permissions и permitted_workout_options — что клиенту можно делать без обращения к владельцу.
planning_previews — серверный расчёт, исходная ревизия, context fingerprint и before/after diff.
schedule_change_requests — только запрос до его одобрения/apply.
Планировочное событие инвалидируется при новых фактах, изменении правил, разрешений и соответствующих источников.
Immutable source может быть архивирован/доступ отозван: apply всё равно перепроверяет доступность.
Ссылки на неизвестные источники в typed diff не исполняются без проверки.

## 7. Видео без жёсткой привязки к одному сервису
exercise_video_submissions — стабильная идентичность одного текущего контрольного ролика на выполненное упражнение.
exercise_video_versions — точный provider/asset/canonical URL по ревизиям. Текущая revision согласуется атомарно.
UI и AI ссылаются на точную версию evidence. Текущее состояние доступа не меняет содержание прошлой оценки.
YouTube/vimeo/google_drive — возможные типы адаптеров, но наличие enum не включает интеграцию.
Не включать в обычные строки/логи access tokens, подписанные приватные URL и скачанный видеоконтент.
Политика удаления/сроков и способ AI-доступа остаются открытыми.

## 8. Тестовая программа без второго тренировочного движка
assessment_protocols уже представляет версии методики: сохраняем protocol_key/version_number вместо дублирующей таблицы версий.
assessment_criteria связывает методику с source exercise slot.
assessment_run_sessions связывает попытку с обычной тренировкой.
assessment_test_runs — только якорь попытки к source_session_exercise, без независимого видео и дублирования set_logs.
assessment_results — версионный общий вывод; assessment_criterion_results — наблюдения по критериям.
Факт хранится один раз; производная оценка указывает, из какой ревизии фактов сделана.

## 9. Авторство, доступ и AI
Не создавать фиктивный профиль тренера для AI. Human actor_user_id либо analysis_run_id + actor_type.
AI не получает привилегированный SQL; валидируемые предложения применяет сервис.
Private coach notes отдельно от client feedback. Доступ AI к ним зависит от конкретной цели/разрешения.
processing_permissions различает персонализацию и обучение общей модели; это не готовый юридический текст.
RLS запускается под runtime без обхода. Context per transaction, без утечки через connection pool.
Billing status и coach access подтверждает сервер, не frontend role/tier selector.

## 10. Структурированные данные
UUID, timestamptz, date, числовые факты, enum/CHECK и FK — основные доменные поля.
JSONB допустим для immutable snapshots, typed rubric/rules, machine diff и evidence manifest.
Нельзя прятать ключевые владельческие связи, mutable список сессий и права в произвольном JSON.
definition схемы валидировать по schema_version; отсутствие данных не интерпретировать как безопасное значение.

## 11. Что надо сделать перед первой SQL-миграцией
Определить фактические baseline имена и порядок FK; циклы evidence/AI допускают staged DDL или deferred constraint.
Создать минимальный auth/profile/catalog/program/plan/training срез, а не все optional AI/chat таблицы заранее.
Определить все unique anchors, partial indexes, row_version, способы публикации и correction.
Проверить property/contract/integration тестами под реальной runtime-ролью.
Сначала локальный изолированный стенд; remote/auth.users не удалять автоматически.
