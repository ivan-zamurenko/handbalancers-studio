# S03-10 — Собрать формы регистрации, кода и входа

**Одна задача:** Accessible component использует готовые auth contracts, показывает pending/error, сохраняет несекретные поля.

| Поле | Значение |
|---|---|
| Порядок | 29 / 134 |
| Модуль | auth |
| Зависит от | S03-09 |
| Внешние gates | Нет для локальной реализации |
| Тип проверки | e2e |
| Статус при выдаче | todo |

## Прочитать один раз для этой задачи
- `docs/auth-contract.md`
Точечные ссылки в этих документах открывать по необходимости. Не перечитывать references/v3 целиком.

## Разрешённая область изменений
- `server/templates/auth/register.html`
- `server/templates/auth/verify.html`
- `server/templates/auth/login.html`
- `server/static/js/features/auth/registration.js`
- `tests/e2e/s03-10-registration-ui.spec.js`

Соседний import/registry разрешён только для подключения этой функции. Расширение scope сначала записать в evidence. `.workflow/CURRENT.md`, `.workflow/state.json` и evidence текущей задачи — допустимые служебные изменения. Пути являются целевыми: большинство runtime/test-файлов ещё не существует.

## Сначала тесты
| Тест | Что обязан доказать |
|---|---|
| `full_signup_keyboard` | Email signup/verification проходят клавиатурой. |
| `no_double_submit` | Быстрый повтор не создаёт два независимых Auth requests. |
| `reload_no_password` | Password не восстанавливается из storage после reload. |
| `error_focus` | Фокус и aria-live у ошибки без прыжка всей страницы. |
| `theme_preserves_form` | Ручная тема не теряет введённое имя/email. |

Команда проверки (создать test-файл до реализации):
```sh
npx playwright test tests/e2e/s03-10-registration-ui.spec.js --project=chromium
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
Социальные кнопки появятся после S04; сейчас не показывать фиктивные working Google/Apple. Имя компонента RegistrationForm — Jinja template + JS controller, не React.

## Критерий завершения
Все указанные проверки действительно выполнены в заявленной среде; обязательные отказы и repeat/concurrency cases сохранены. Нет skip/xfail вместо требуемой гарантии. Новый API подключён в app только после соответствующих guards. Нет фиктивных данных в production-экране. Есть проверяемый результат и узкий diff.

Если зависимость/ключи недоступны, сохранить blocker и перейти только к следующей реально доступной независимой задаче. Нельзя объявить внешнюю функцию готовой по mock. Возникший дефект чужого модуля получает отдельную карточку, не скрытый rewrite.

## Коммит и передача
Ветка после baseline: `task/s03-10-registration-ui`.
```sh
git diff --check
git status --short
# Stage ONLY reviewed paths from this task; never blindly git add .
git diff --cached --stat
git diff --cached --check
git commit -m "feat(auth): [S03-10] registration ui"
# After remote and branch authorization: git push -u origin <task-branch>
```
Шаблон команды push намеренно не исполняется с неподтверждённым origin. Если remote отсутствует — локальный commit и push_status=pending, не blocker кодирования.

Evidence: `.workflow/evidence/S03-10.json` по шаблону. Собственный SHA коммита не записывать внутрь того же коммита: branch/ref и base SHA до commit, итоговый SHA — в ответе/следующем checkpoint. Интегратор отмечает task done после проверки; dependency для следующего writer должна быть реально в его checkout.
