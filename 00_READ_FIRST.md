# Handbalancer’s Studio — execution kit v4

**Начать писать новый код с S00-01.** Это новая реализация в отдельной папке, без переноса старых аккаунтов и без удаления старого проекта. План охватывает клиентскую часть и админку как один продукт.

В комплекте 134 задачи в 18 стадиях; каждая имеет цель, зависимости, файлы, test-first проверки, API/DB контракт и commit subject. Это план, не отметка, что соответствующий код существует. Все application tasks — todo.

## Старт
1. Прочитать `AGENTS.md` и `.workflow/CURRENT.md`.
2. Выполнить `python tools/roadmap.py next`.
3. Открыть карточку и релевантные документы. Выполнить одну ответственность до проверенного GREEN.
4. Обновить evidence/state/checkpoint; reviewed commit, разрешённый push. Не возвращаться к общему планированию.

Человек: `START_HERE.html` — навигация и поиск; `docs/owner-workflow.md` — управление агентами; `agent-config/README_RU.md` — режимы Astra.
Агент: `AGENT_START_RU.txt` — готовое первое сообщение; `.agents/skills/studio-task-delivery` — project workflow.

## Приоритет
Последнее явное решение владельца → docs/decisions.md → v4 карточки и engineering-defaults/contracts/database-invariants → reference v3 → исторический MODEL_HANDOFF. Старое «не начинать заново» отменено последним поручением, но удалять прежнюю работу нельзя. Нормативные значения нагрузки и внешние провайдеры не подменяются инженерными defaults.

## Чего здесь нет
Нет app runtime, production SQL, выполненного git push, подключённых Google/Apple/Stripe, настоящего AI/video pipeline или разрешения на запуск расходов. Опциональный adapter под ещё неизвестный сервис разбивается на небольшие дочерние задачи после решения владельца; выдумывать его сейчас не нужно.

Не импортировать references в контекст целиком. Reference design state selectors/демо-данные не переносить как product authorization. Fonts не входят в комплект.
