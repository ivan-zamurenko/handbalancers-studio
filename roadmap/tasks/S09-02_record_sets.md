# S09-02 — Сохранить факт подхода с optimistic concurrency

**Одна задача:** PUT по стабильному log_id сохраняет typed result или explicit skip.

| Поле | Значение |
|---|---|
| Порядок | 66 / 134 |
| Модуль | training |
| Зависит от | S09-01 |
| Внешние gates | Нет для локальной реализации |
| Тип проверки | integration |
| Статус при выдаче | todo |

## Прочитать один раз для этой задачи
- `docs/contracts.md`
- `docs/frontend.md`
Точечные ссылки в этих документах открывать по необходимости. Не перечитывать references/v3 целиком.

## Разрешённая область изменений
- `server/studio/training/set_logs.py`
- `server/alembic/versions/0025_set_logs.py`
- `server/tests/integration/training/test_record_sets.py`

Соседний import/registry разрешён только для подключения этой функции. Расширение scope сначала записать в evidence. `.workflow/CURRENT.md`, `.workflow/state.json` и evidence текущей задачи — допустимые служебные изменения. Пути являются целевыми: большинство runtime/test-файлов ещё не существует.

## Сначала тесты
| Тест | Что обязан доказать |
|---|---|
| `retry_same_log_no_duplicate` | Повтор PUT с тем же log id не создаёт новую строку. |
| `stale_revision_409` | Два устройства не перезаписывают друг друга. |
| `missing_zero_skip_distinct` | NULL/0/skipped не нормализуются в одно значение. |
| `foreign_target_denied` | Target должен принадлежать source prescription session exercise. |
| `completed_ordinary_edit_denied` | Обычный PUT не редактирует terminal session. |

Команда проверки (создать test-файл до реализации):
```sh
uv run pytest server/tests/integration/training/test_record_sets.py -q
```

Ожидаемый RED: как минимум один из новых тестов выявляет именно отсутствующее поведение текущей карточки. Ошибки настройки исправляются отдельно и не выдаются за TDD-доказательство. Для чисто инфраструктурной задачи проверяется её реальная гарантия, а не assert(true).

## HTTP / компонентный контракт
PUT /api/sessions/{id}/set-logs/{log_id} {session_exercise_id,target_set_id,set_number,side,status,reps|duration_ms|load_kg,expected_revision}.

## Изменение данных
0025: studio.set_logs; unique(session_exercise_id,set_number,side), CHECK tracking result; owner composite FK/trigger.
Автоматическая генерация Alembic — черновик: проверить вручную ограничения, grants/RLS, downgrade/forward-repair, schema qualifiers. Не применять к старой/production БД.

## Выполнение
1. Проверить зависимости, рабочую ветку и узкий diff. Загрузить только файлы текущей карточки и связанные типы.
2. Написать тесты поведения из таблицы ниже. API/инварианты берутся из карточки, не из будущей реализации.
3. Запустить указанную команду и записать реальный RED. Причина — отсутствующая функция/нарушенная ожидаемая гарантия, не выключенная БД или отсутствующий пакет.
4. Реализовать минимальную ответственность этой карточки. При новом model/FK создать только указанную миграцию, grants/RLS и негативные проверки.
5. Получить GREEN этой команды; запустить затронутый regression subset. Для UI открыть 390/1440 и обе темы; для DB выполнить upgrade на чистой test-среде и isolation/concurrency checks.
6. Убрать дублирование только внутри затронутого кода. Повторно проверить изменившиеся зависимости, не прогонять неизменённый полный suite по кругу.
7. Обновить evidence/CURRENT/state. Проверить diff/secrets, создать один GREEN-коммит с тестами и реализацией. Push только в подтверждённый remote ветки задачи. Не делать автоматический merge/deploy.

## Особые условия
Успешный факт увеличивает session data_revision и plan context_revision, чтобы stale planner preview не применился поверх новых данных.

## Критерий завершения
Все указанные проверки действительно выполнены в заявленной среде; обязательные отказы и repeat/concurrency cases сохранены. Нет skip/xfail вместо требуемой гарантии. Новый API подключён в app только после соответствующих guards. Нет фиктивных данных в production-экране. Есть проверяемый результат и узкий diff.

Если зависимость/ключи недоступны, сохранить blocker и перейти только к следующей реально доступной независимой задаче. Нельзя объявить внешнюю функцию готовой по mock. Возникший дефект чужого модуля получает отдельную карточку, не скрытый rewrite.

## Коммит и передача
Ветка после baseline: `task/s09-02-record-sets`.
```sh
git diff --check
git status --short
# Stage ONLY reviewed paths from this task; never blindly git add .
git diff --cached --stat
git diff --cached --check
git commit -m "feat(training): [S09-02] record sets"
# After remote and branch authorization: git push -u origin <task-branch>
```
Шаблон команды push намеренно не исполняется с неподтверждённым origin. Если remote отсутствует — локальный commit и push_status=pending, не blocker кодирования.

Evidence: `.workflow/evidence/S09-02.json` по шаблону. Собственный SHA коммита не записывать внутрь того же коммита: branch/ref и base SHA до commit, итоговый SHA — в ответе/следующем checkpoint. Интегратор отмечает task done после проверки; dependency для следующего writer должна быть реально в его checkout.
