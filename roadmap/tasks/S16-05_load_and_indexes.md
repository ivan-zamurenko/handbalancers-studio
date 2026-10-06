# S16-05 — Измерить реальные узкие места перед оптимизацией

**Одна задача:** Набор synthetic клиентов/истории, query count, plan-preview bounded runtime, DB pool budget.

| Поле | Значение |
|---|---|
| Порядок | 126 / 134 |
| Модуль | operations |
| Зависит от | S16-04 |
| Внешние gates | Нет для локальной реализации |
| Тип проверки | tooling |
| Статус при выдаче | todo |

## Прочитать один раз для этой задачи
- `docs/testing-and-commits.md`
- `docs/owner-gates.md`
Точечные ссылки в этих документах открывать по необходимости. Не перечитывать references/v3 целиком.

## Разрешённая область изменений
- `tools/benchmarks/`
- `docs/verification/performance.md`
- `server/alembic/versions/0048_measured_indexes.py`
- `tools/tests/test_s16_05_load_and_indexes.py`

Соседний import/registry разрешён только для подключения этой функции. Расширение scope сначала записать в evidence. `.workflow/CURRENT.md`, `.workflow/state.json` и evidence текущей задачи — допустимые служебные изменения. Пути являются целевыми: большинство runtime/test-файлов ещё не существует.

## Сначала тесты
| Тест | Что обязан доказать |
|---|---|
| `bounded_list_queries` | Cursor pagination ограничивает rows, нет N+1 на roster/history. |
| `planner_bound` | Ограниченный horizon не вызывает бесконечную комбинацию. |
| `pool_budget` | Web/auth/worker pools не превышают выделенный connection budget. |
| `index_evidence` | Каждый новый индекс имеет объяснение query plan/потребности. |

Команда проверки (создать test-файл до реализации):
```sh
python -m unittest discover -s tools/tests -p test_s16_05_load_and_indexes.py -v
```

Ожидаемый RED: как минимум один из новых тестов выявляет именно отсутствующее поведение текущей карточки. Ошибки настройки исправляются отдельно и не выдаются за TDD-доказательство. Для чисто инфраструктурной задачи проверяется её реальная гарантия, а не assert(true).

## HTTP / компонентный контракт
Нет нового публичного API.

## Изменение данных
Нет изменения схемы.
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
Целевые latency/нагрузка — рабочие SLO, фиксируются как допущения, не гарантия MacBook/стоимости. Не вводить cache/queue/microservices без измеренного bottleneck.

## Критерий завершения
Все указанные проверки действительно выполнены в заявленной среде; обязательные отказы и repeat/concurrency cases сохранены. Нет skip/xfail вместо требуемой гарантии. Новый API подключён в app только после соответствующих guards. Нет фиктивных данных в production-экране. Есть проверяемый результат и узкий diff.

Если зависимость/ключи недоступны, сохранить blocker и перейти только к следующей реально доступной независимой задаче. Нельзя объявить внешнюю функцию готовой по mock. Возникший дефект чужого модуля получает отдельную карточку, не скрытый rewrite.

## Коммит и передача
Ветка после baseline: `task/s16-05-load-and-indexes`.
```sh
git diff --check
git status --short
# Stage ONLY reviewed paths from this task; never blindly git add .
git diff --cached --stat
git diff --cached --check
git commit -m "feat(operations): [S16-05] load and indexes"
# After remote and branch authorization: git push -u origin <task-branch>
```
Шаблон команды push намеренно не исполняется с неподтверждённым origin. Если remote отсутствует — локальный commit и push_status=pending, не blocker кодирования.

Evidence: `.workflow/evidence/S16-05.json` по шаблону. Собственный SHA коммита не записывать внутрь того же коммита: branch/ref и base SHA до commit, итоговый SHA — в ответе/следующем checkpoint. Интегратор отмечает task done после проверки; dependency для следующего writer должна быть реально в его checkout.
