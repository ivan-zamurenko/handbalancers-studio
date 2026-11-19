# S05-02 — Перенести гостевую анкету через вход

**Одна задача:** Маршрут цели → тариф → регистрация/вход сохраняет несекретный draft, не перезаписывая профиль существующего пользователя.

| Поле | Значение |
|---|---|
| Порядок | 38 / 134 |
| Модуль | onboarding |
| Зависит от | S05-01 |
| Внешние gates | Нет для локальной реализации |
| Тип проверки | e2e |
| Статус при выдаче | todo |

## Прочитать один раз для этой задачи
- `docs/contracts.md`
- `docs/decisions.md`
Точечные ссылки в этих документах открывать по необходимости. Не перечитывать references/v3 целиком.

## Разрешённая область изменений
- `server/templates/public/onboarding.html`
- `server/static/js/features/onboarding/form.js`
- `server/studio/accounts/onboarding_routes.py`
- `tests/e2e/s05-02-guest-onboarding.spec.js`

Соседний import/registry разрешён только для подключения этой функции. Расширение scope сначала записать в evidence. `.workflow/CURRENT.md`, `.workflow/state.json` и evidence текущей задачи — допустимые служебные изменения. Пути являются целевыми: большинство runtime/test-файлов ещё не существует.

## Сначала тесты
| Тест | Что обязан доказать |
|---|---|
| `fresh_days_empty` | В новой анкете нет выбранных дней. |
| `existing_account_no_silent_overwrite` | После login существующая анкета не заменена guest draft без подтверждения. |
| `selected_dom_value` | Browser-restored radio 90 учитывается даже без change event. |
| `reduced_motion_no_click_loss` | Быстрый submit/swipe не теряет выбор. |

Команда проверки (создать test-файл до реализации):
```sh
npx playwright test tests/e2e/s05-02-guest-onboarding.spec.js --project=chromium
```

Ожидаемый RED: как минимум один из новых тестов выявляет именно отсутствующее поведение текущей карточки. Ошибки настройки исправляются отдельно и не выдаются за TDD-доказательство. Для чисто инфраструктурной задачи проверяется её реальная гарантия, а не assert(true).

## HTTP / компонентный контракт
POST /api/onboarding/draft (pre-auth CSRF); PUT /api/me/onboarding (trusted actor,expected_revision).

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
Никакого дополнительного поведения сверх цели и тестов карточки.

## Критерий завершения
Все указанные проверки действительно выполнены в заявленной среде; обязательные отказы и repeat/concurrency cases сохранены. Нет skip/xfail вместо требуемой гарантии. Новый API подключён в app только после соответствующих guards. Нет фиктивных данных в production-экране. Есть проверяемый результат и узкий diff.

Если зависимость/ключи недоступны, сохранить blocker и перейти только к следующей реально доступной независимой задаче. Нельзя объявить внешнюю функцию готовой по mock. Возникший дефект чужого модуля получает отдельную карточку, не скрытый rewrite.

## Коммит и передача
Ветка после baseline: `task/s05-02-guest-onboarding`.
```sh
git diff --check
git status --short
# Stage ONLY reviewed paths from this task; never blindly git add .
git diff --cached --stat
git diff --cached --check
git commit -m "feat(onboarding): [S05-02] guest onboarding"
# After remote and branch authorization: git push -u origin <task-branch>
```
Шаблон команды push намеренно не исполняется с неподтверждённым origin. Если remote отсутствует — локальный commit и push_status=pending, не blocker кодирования.

Evidence: `.workflow/evidence/S05-02.json` по шаблону. Собственный SHA коммита не записывать внутрь того же коммита: branch/ref и base SHA до commit, итоговый SHA — в ответе/следующем checkpoint. Интегратор отмечает task done после проверки; dependency для следующего writer должна быть реально в его checkout.


## Погоджене уточнення власника — 2026-11-19

Follow-up до виконаної S05-02: completion-based entry та збереження форми при зміні мови.
Кількість входів не критерій: незавершена анкета → profile; завершена → dashboard.
Новий dashboard має серверний guard, але лише чесний порожній стан до S08–S09.
Публічні сторінки не блокуються. Після першого save — dashboard; явне редагування — profile.
Мова й тема не перезавантажують документ і не стирають вибрані пункти.

Область: accounts/entry.py, public routes/templates, OAuth default return path,
auth/session/profile JS, спільний i18n модуль із public copy pairs, вузькі DB/e2e тести.
Без SQL/міграцій, зміни provider integrations або цін. Докази:
`.workflow/evidence/onboarding-entry-2026-11-19.json`.

Приймання: повторний вхід без анкети не обходить guard; завершений акаунт з іншого
пристрою не отримує онбординг; недійсна сесія → login, збій БД → 503; новий Google
callback → guard; UA/EN/тема зберігають DOM, крок і вибір на 390/1440; пароль не в storage.
Commit: `fix(onboarding): [S05-02] completion-aware entry and live language`.
