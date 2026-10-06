# S03-03 — Принять регистрацию email/password

**Одна задача:** POST валидирует имя, фамилию, email/password и вызывает Supabase, не выдавая доступ до verification.

| Поле | Значение |
|---|---|
| Порядок | 22 / 134 |
| Модуль | auth |
| Зависит от | S03-02 |
| Внешние gates | Нет для локальной реализации |
| Тип проверки | contracts |
| Статус при выдаче | todo |

## Прочитать один раз для этой задачи
- `docs/auth-contract.md`
Точечные ссылки в этих документах открывать по необходимости. Не перечитывать references/v3 целиком.

## Разрешённая область изменений
- `server/studio/auth/schemas.py`
- `server/studio/auth/service.py`
- `server/studio/auth/routes.py`
- `server/tests/contracts/auth/test_signup_request.py`

Соседний import/registry разрешён только для подключения этой функции. Расширение scope сначала записать в evidence. `.workflow/CURRENT.md`, `.workflow/state.json` и evidence текущей задачи — допустимые служебные изменения. Пути являются целевыми: большинство runtime/test-файлов ещё не существует.

## Сначала тесты
| Тест | Что обязан доказать |
|---|---|
| `valid_signup_pending` | 202 {state:verification_pending}; нет authenticated cookie и studio.users. |
| `invalid_input_no_upstream` | Пустое имя/невалидная почта/недопустимый пароль дают 422 до Auth call. |
| `existing_email_generic` | По существующему email ответ не раскрывает существование аккаунта. |
| `no_password_in_database` | Password отсутствует в product/private tables и logs. |
| `provider_unavailable` | 503 retryable без выдачи доступа. |

Команда проверки (создать test-файл до реализации):
```sh
uv run pytest server/tests/contracts/auth/test_signup_request.py -q
```

Ожидаемый RED: как минимум один из новых тестов выявляет именно отсутствующее поведение текущей карточки. Ошибки настройки исправляются отдельно и не выдаются за TDD-доказательство. Для чисто инфраструктурной задачи проверяется её реальная гарантия, а не assert(true).

## HTTP / компонентный контракт
POST /api/auth/register {first_name,last_name,email,password} → 202 {state:"verification_pending"}; 422/429/503 по контракту.

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
Supabase может создать pending auth.users до подтверждения. «Аккаунт создан после кода» здесь означает активный product profile/session после verified identity, не отсутствие любой managed Auth строки.

## Критерий завершения
Все указанные проверки действительно выполнены в заявленной среде; обязательные отказы и repeat/concurrency cases сохранены. Нет skip/xfail вместо требуемой гарантии. Новый API подключён в app только после соответствующих guards. Нет фиктивных данных в production-экране. Есть проверяемый результат и узкий diff.

Если зависимость/ключи недоступны, сохранить blocker и перейти только к следующей реально доступной независимой задаче. Нельзя объявить внешнюю функцию готовой по mock. Возникший дефект чужого модуля получает отдельную карточку, не скрытый rewrite.

## Коммит и передача
Ветка после baseline: `task/s03-03-signup-request`.
```sh
git diff --check
git status --short
# Stage ONLY reviewed paths from this task; never blindly git add .
git diff --cached --stat
git diff --cached --check
git commit -m "feat(auth): [S03-03] signup request"
# After remote and branch authorization: git push -u origin <task-branch>
```
Шаблон команды push намеренно не исполняется с неподтверждённым origin. Если remote отсутствует — локальный commit и push_status=pending, не blocker кодирования.

Evidence: `.workflow/evidence/S03-03.json` по шаблону. Собственный SHA коммита не записывать внутрь того же коммита: branch/ref и base SHA до commit, итоговый SHA — в ответе/следующем checkpoint. Интегратор отмечает task done после проверки; dependency для следующего writer должна быть реально в его checkout.
