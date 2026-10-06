# S04-05 — Выдать владельцу coach вне публичной регистрации

**Одна задача:** CLI повышает роль ровно подтверждённому auth_user_id с аудитом.

| Поле | Значение |
|---|---|
| Порядок | 35 / 134 |
| Модуль | accounts |
| Зависит от | S04-04 |
| Внешние gates | Нет для локальной реализации |
| Тип проверки | security |
| Статус при выдаче | todo |

## Прочитать один раз для этой задачи
- `docs/auth-contract.md`
- `docs/owner-gates.md`
Точечные ссылки в этих документах открывать по необходимости. Не перечитывать references/v3 целиком.

## Разрешённая область изменений
- `server/studio/accounts/cli.py`
- `server/studio/accounts/roles.py`
- `server/alembic/versions/0006_audit.py`
- `server/tests/security/accounts/test_coach_bootstrap.py`

Соседний import/registry разрешён только для подключения этой функции. Расширение scope сначала записать в evidence. `.workflow/CURRENT.md`, `.workflow/state.json` и evidence текущей задачи — допустимые служебные изменения. Пути являются целевыми: большинство runtime/test-файлов ещё не существует.

## Сначала тесты
| Тест | Что обязан доказать |
|---|---|
| `member_cannot_promote` | Нет public endpoint/metadata пути к coach. |
| `verified_owner_only` | CLI отвергает unverified/missing identity. |
| `repeat_bootstrap_no_duplicate` | Повтор не создаёт вторую identity или профиль. |
| `role_revocation_effective` | Следующий защищённый запрос учитывает актуальную роль из БД. |

Команда проверки (создать test-файл до реализации):
```sh
uv run pytest server/tests/security/accounts/test_coach_bootstrap.py -q
```

Ожидаемый RED: как минимум один из новых тестов выявляет именно отсутствующее поведение текущей карточки. Ошибки настройки исправляются отдельно и не выдаются за TDD-доказательство. Для чисто инфраструктурной задачи проверяется её реальная гарантия, а не assert(true).

## HTTP / компонентный контракт
Нет нового публичного API.

## Изменение данных
0006: studio_private.audit_events; actor_type human|system, analysis_run_id FK добавить только в AI stage.
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
Авторизация запуска operator CLI отдельно от знания email. Не делать первым зарегистрированным пользователем администратора.

## Критерий завершения
Все указанные проверки действительно выполнены в заявленной среде; обязательные отказы и repeat/concurrency cases сохранены. Нет skip/xfail вместо требуемой гарантии. Новый API подключён в app только после соответствующих guards. Нет фиктивных данных в production-экране. Есть проверяемый результат и узкий diff.

Если зависимость/ключи недоступны, сохранить blocker и перейти только к следующей реально доступной независимой задаче. Нельзя объявить внешнюю функцию готовой по mock. Возникший дефект чужого модуля получает отдельную карточку, не скрытый rewrite.

## Коммит и передача
Ветка после baseline: `task/s04-05-coach-bootstrap`.
```sh
git diff --check
git status --short
# Stage ONLY reviewed paths from this task; never blindly git add .
git diff --cached --stat
git diff --cached --check
git commit -m "feat(accounts): [S04-05] coach bootstrap"
# After remote and branch authorization: git push -u origin <task-branch>
```
Шаблон команды push намеренно не исполняется с неподтверждённым origin. Если remote отсутствует — локальный commit и push_status=pending, не blocker кодирования.

Evidence: `.workflow/evidence/S04-05.json` по шаблону. Собственный SHA коммита не записывать внутрь того же коммита: branch/ref и base SHA до commit, итоговый SHA — в ответе/следующем checkpoint. Интегратор отмечает task done после проверки; dependency для следующего writer должна быть реально в его checkout.
