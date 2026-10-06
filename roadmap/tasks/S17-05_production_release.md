# S17-05 — Выпустить только утверждённый релиз с rollback планом

**Одна задача:** Reviewed commit/tag, backup, controlled migrations, smoke, metrics и отдельное разрешение production.

| Поле | Значение |
|---|---|
| Порядок | 134 / 134 |
| Модуль | release |
| Зависит от | S17-01, S17-04, S16-07, S16-08 |
| Внешние gates | G_PRODUCTION |
| Тип проверки | gate |
| Статус при выдаче | todo |

## Прочитать один раз для этой задачи
- `docs/owner-gates.md`
Точечные ссылки в этих документах открывать по необходимости. Не перечитывать references/v3 целиком.

## Разрешённая область изменений
- `docs/release/release-checklist.md`
- `docs/runbooks/deployment.md`
- `docs/verification/S17-05-external-check.md`

Соседний import/registry разрешён только для подключения этой функции. Расширение scope сначала записать в evidence. `.workflow/CURRENT.md`, `.workflow/state.json` и evidence текущей задачи — допустимые служебные изменения. Пути являются целевыми: большинство runtime/test-файлов ещё не существует.

## Сначала тесты
| Тест | Что обязан доказать |
|---|---|
| `authorized_target` | Domain/VPS/Supabase/Stripe live конфигурации явно утверждены. |
| `restore_and_rollback_ready` | Restore rehearsal и rollback/forward-fix доступны. |
| `verified_sha` | Deploy соответствует reviewed commit, не dirty tree. |
| `postdeploy_smoke` | Login/own data/core journey проверены без реальных нежелательных списаний. |
| `monitor_and_stop` | Kill switches и операторские контакты определены. |

Команда проверки (создать test-файл до реализации):
```sh
python tools/roadmap.py show S17-05
```

Для внешнего допуска не изображать RED несуществующего unit-test: перед запуском фиксируются сценарии и фактический результат. Любой новый runtime-код внутри допуска сначала получает свою TDD-подзадачу.

## HTTP / компонентный контракт
Нет нового публичного API.

## Изменение данных
Нет изменения схемы.
Автоматическая генерация Alembic — черновик: проверить вручную ограничения, grants/RLS, downgrade/forward-repair, schema qualifiers. Не применять к старой/production БД.

## Выполнение
1. Проверить, что gates действительно разрешены владельцем и доступны в staging; не просить secrets в чат.
2. До проверки записать expected outcomes из таблицы ниже. Если нужен новый adapter, сначала выделить маленькие TDD-subtasks, а не писать его одним большим gate-коммитом.
3. Выполнить реальные разрешённые сценарии; зафиксировать дату, среду, версию, безопасный результат.
4. Недоступный сервис = blocked/pending, не pass. Тесты с fake не заменяют эту карточку.
5. Коммитить проверенный adapter либо редактированный evidence отдельно по ответственности; deployment остаётся отдельным разрешением.

## Особые условия
Не выполнять deployment из этого handoff. Подготовка артефакта не является разрешением на production или создание расходов.

## Критерий завершения
Все указанные проверки действительно выполнены в заявленной среде; обязательные отказы и repeat/concurrency cases сохранены. Нет skip/xfail вместо требуемой гарантии. Новый API подключён в app только после соответствующих guards. Нет фиктивных данных в production-экране. Есть проверяемый результат и узкий diff.

Если зависимость/ключи недоступны, сохранить blocker и перейти только к следующей реально доступной независимой задаче. Нельзя объявить внешнюю функцию готовой по mock. Возникший дефект чужого модуля получает отдельную карточку, не скрытый rewrite.

## Коммит и передача
Ветка после baseline: `task/s17-05-production-release`.
```sh
git diff --check
git status --short
# Stage ONLY reviewed paths from this task; never blindly git add .
git diff --cached --stat
git diff --cached --check
git commit -m "feat(release): [S17-05] production release"
# After remote and branch authorization: git push -u origin <task-branch>
```
Шаблон команды push намеренно не исполняется с неподтверждённым origin. Если remote отсутствует — локальный commit и push_status=pending, не blocker кодирования.

Evidence: `.workflow/evidence/S17-05.json` по шаблону. Собственный SHA коммита не записывать внутрь того же коммита: branch/ref и base SHA до commit, итоговый SHA — в ответе/следующем checkpoint. Интегратор отмечает task done после проверки; dependency для следующего writer должна быть реально в его checkout.
