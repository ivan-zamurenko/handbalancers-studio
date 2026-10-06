# Контракты операций — проектная отправная точка

Это не OpenAPI существующего backend. Перед реализацией сверить маршруты рабочего репозитория, затем зафиксировать и протестировать итоговые схемы.
Общие правила: доверенный actor из сессии; entitlement на сервере; request validation; idempotency для повторяемого эффекта; expected_revision для конкуренции.

## Основные команды
| Команда | Смысл |
|---|---|
| `GET /api/me/plan` | Единый план клиента, текущая основная программа и реальные occurrence |
| `GET /api/catalog/programs` | Опубликованные общие программы с проверкой доступа |
| `POST /api/plans/{id}/previews` | Рассчитать replace_main / replace_workout / add_additional / move_workout |
| `POST /api/plans/{id}/previews/{preview_id}/apply` | Атомарно применить подтверждённый и актуальный diff |
| `POST /api/plans/{id}/change-requests` | Запрос клиентом неразрешённого изменения; календарь пока не меняется |
| `POST /api/coach/change-requests/{id}/approve` | Свежая проверка + apply; не слепое применение старого запроса |
| `POST /api/coach/change-requests/{id}/reject` | Причина и видимый результат рассмотрения |
| `PATCH /api/coach/plans/{id}/permissions` | Разрешения клиента и утверждённые варианты |
| `POST /api/program-versions/{id}/publish` | Валидация и заморозка дерева |
| `POST /api/scheduled-workouts/{id}/start` | Одна guided session и её snapshots |
| `PUT /api/sessions/{id}/set-logs/{log_id}` | Стабильный лог подхода + expected row revision |
| `POST /api/sessions/{id}/pause` / `resume` | Согласованное время и состояние |
| `POST /api/sessions/{id}/complete` | Атомарный факт + occurrence + отчёт |
| `POST /api/session-exercises/{id}/video` | Новая версия контрольной ссылки |
| `POST /api/coach/reviews/{id}/publish` | Неизменяемая версия feedback, без изменения программы |
| `POST /api/analysis/proposals/{id}/apply` | Доверенный apply допустимой AI-адаптации |
| `PATCH /api/me/preferences` | auto/light/dark + expected revision |

## Preview
```json
{
  "operation": "replace_workout",
  "target_occurrence_id": "<uuid>",
  "source_program_workout_id": "<uuid>",
  "source_program_version_id": "<uuid>",
  "date": "2026-10-07",
  "expected_plan_revision": 12
}
```
Дата — пример формата, не фиксированная дата для seed/production. IDs — placeholders, не реальные записи.
Сервер проверяет принадлежность target, опубликованность и доступность source, режим управления, разрешения, совместимость, контекст.
Ответ содержит preview_id, outcome, base revision, expires_at, объяснения и структурированный diff before/after.
При выборе только дня не выдумывать время начала.

## Apply
```json
{
  "expected_plan_revision": 12,
  "idempotency_key": "<unique-command-key>"
}
```
Вход не содержит произвольный SQL/diff для исполнения: применяется серверный preview.
Транзакция проверяет владельца, доступ, статус/срок preview, актуальный контекст выполнения, assignment/rules/revision.
Терминальные и начатые occurrence не изменяются. История не переписывается.
Если preview устарел — 409 и новый расчёт; не молчаливое применение.
Для недоступных прав — соответствующая ошибка доступа; для невалидных данных — validation; для недостаточного evidence — явный продуктовый outcome.
Конкретные HTTP-коды закрепить контрактными тестами, не смешивать финансовый отказ с «не найдено».

## Авторство
Member/coach имеют actor_user_id. AI фиксирует analysis_run_id и тип actor; не создавать фиктивного пользователя-тренера.
Публикация от AI разрешается только доверенному сервису в утверждённых пределах.
Параметр user_id в URL админки не заменяет проверку coach access.
