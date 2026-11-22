# S13-09 — Проверить реальную test-mode интеграцию отдельно от mocks

**Одна задача:** Stripe test fixtures/CLI проходят подпись, webhook и lifecycle с искусственными клиентами.

| Поле | Значение |
|---|---|
| Порядок | 109 / 134 |
| Модуль | billing |
| Зависит от | S13-09a |
| Внешние gates | G_STRIPE_TEST |
| Тип проверки | gate |
| Статус при выдаче | todo |

## Прочитать один раз для этой задачи
- `docs/contracts.md`
- `docs/owner-gates.md`
Точечные ссылки в этих документах открывать по необходимости. Не перечитывать references/v3 целиком.

## Разрешённая область изменений
- `docs/verification/stripe-testmode.md`
- `tools/stripe_testmode.py`
- `docs/verification/S13-09-external-check.md`

Соседний import/registry разрешён только для подключения этой функции. Расширение scope сначала записать в evidence. `.workflow/CURRENT.md`, `.workflow/state.json` и evidence текущей задачи — допустимые служебные изменения. Пути являются целевыми: большинство runtime/test-файлов ещё не существует.

## Сначала тесты
| Тест | Что обязан доказать |
|---|---|
| `real_test_checkout` | Подтверждена actual test Checkout session без live списания. |
| `real_signature` | CLI event проверен реальной библиотекой подписи. |
| `trial_end_lifecycle` | Test Clock/поддержанный сценарий проверяет конец trial. |
| `no_live_environment` | Инструмент отказывается от live keys/objects. |

Команда проверки (создать test-файл до реализации):
```sh
python tools/roadmap.py show S13-09
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
Нет credentials/разрешённого endpoint — env_blocked, не fake passed. Эта task не блокирует последующую разработку AI contracts. Ничего не создавать в live Stripe без разрешения.

## Критерий завершения
Все указанные проверки действительно выполнены в заявленной среде; обязательные отказы и repeat/concurrency cases сохранены. Нет skip/xfail вместо требуемой гарантии. Новый API подключён в app только после соответствующих guards. Нет фиктивных данных в production-экране. Есть проверяемый результат и узкий diff.

Если зависимость/ключи недоступны, сохранить blocker и перейти только к следующей реально доступной независимой задаче. Нельзя объявить внешнюю функцию готовой по mock. Возникший дефект чужого модуля получает отдельную карточку, не скрытый rewrite.

## Коммит и передача
Ветка после baseline: `task/s13-09-billing-testmode`.
```sh
git diff --check
git status --short
# Stage ONLY reviewed paths from this task; never blindly git add .
git diff --cached --stat
git diff --cached --check
git commit -m "feat(billing): [S13-09] billing testmode"
# After remote and branch authorization: git push -u origin <task-branch>
```
Шаблон команды push намеренно не исполняется с неподтверждённым origin. Если remote отсутствует — локальный commit и push_status=pending, не blocker кодирования.

Evidence: `.workflow/evidence/S13-09.json` по шаблону. Собственный SHA коммита не записывать внутрь того же коммита: branch/ref и base SHA до commit, итоговый SHA — в ответе/следующем checkpoint. Интегратор отмечает task done после проверки; dependency для следующего writer должна быть реально в его checkout.
