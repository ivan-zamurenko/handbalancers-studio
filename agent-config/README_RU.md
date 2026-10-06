# Настройка GPT-6 Astra для разработки

Проверено по официальным страницам OpenAI на 2026-10-06: API ID `gpt-6-astra`; reasoning.effort low/medium/high/xhigh/max [S-MODEL]. Это не выдуманный slug «gpt-6-astra-pro». Подписка ChatGPT, доступный API model, выбранный режим и разрешения инструментов — разные настройки.

## Что подготовлено
`.codex/config.toml` — project-scoped конфигурация для обычной реализации: high, workspace-write, on-request, один concurrent subagent. `.codex/agents/reviewer.toml` — max/read-only review. `quality.config.toml.example` — отдельные проверенные значения для максимального reasoning, не обещание «самого быстрого» режима. `responses-quality.example.json` — пример API input, не выполнение запроса и не AI-провайдер для видео продукта.

Рабочий launch после установки/проверки актуального Codex и trust проекта:
```sh
codex -m gpt-6-astra -c 'model_reasoning_effort="high"'
```
Сложный auth/security/DB race review:
```sh
codex -m gpt-6-astra -c 'model_reasoning_effort="max"'
```
По требованию владельца max можно использовать и для всех implementation задач; high здесь — мой baseline для баланса, не официальное обязательное правило. Higher reasoning не означает меньшую задержку. Сначала task clarity и targeted tools, затем повышение effort. Не включать платный fast tier без понимания бюджета.

## Codex и обычный ChatGPT — не одно и то же
Project config загружается в доверенном coding workspace [S-CONFIG]. В обычном чате загрузка TOML как вложения сама по себе не меняет model/effort или shell permissions. В ChatGPT выбрать доступный режим через интерфейс, добавить `prompts/CHATGPT_PROJECT_RU.md` как project instructions и приложить task/checkpoint. Кодовые команды требуют среды с реальным checkout и разрешённым запуском; модель не должна притворяться, что выполнила тесты без shell.

Не создавать сотни глобальных инструкций, не обещать отключение compaction/«безлимитный контекст». AGENTS.md — краткий repo contract, CURRENT — состояние, карточка — задача. Длинные docs загружаются только по релевантности [S-AGENTS][S-SKILLBLOG]. `reasoning` API JSON не вставляется вместо Codex TOML; имя API поля отличается.

## Разрешения без лишних остановок
Read/edit в новом workspace и локальные тесты заранее разрешены в пределах задачи. `on-request` остаётся для расширения sandbox, установки зависимостей/локальных сервисов и требуемой сети. Network=false может потребовать отдельного разрешения локального Supabase/Playwright подключения: настроить разрешённые локальные команды в своей среде один раз, не заменять на unrestricted режим.

Sandbox shell не является полной policy для MCP/connectors. Их доступ отдельно ограничить dev/staging, production read-only по умолчанию. Ни один файл prompt не должен отменять платформенные правила или разрешать реальные оплаты/передачу видео.

Remote push: после однократного подтверждения origin и task-branch workflow разрешить обычный push ветки, без force/main/deploy. Автономность означает завершить одну задачу, а не изменить всё окружение.

## Подагенты
Один writer + один read-only reviewer — предлагаемый рабочий режим, не универсальная производительность в цифрах. Concurrent subagent limit=1 исключает primary thread [S-CONFIG]. Более одного writer подключать только к непересекающимся задачам/файлам после устойчивого skeleton. Branch/worktree/database/ports должны быть отдельными. Главный интегратор владеет миграциями, API и status state. Не делить одну авторизацию на независимых writer без согласованного DTO.

## Проверка настроек
В этом комплекте TOML разобран парсером и ключи сверены с docs; Codex CLI здесь отсутствует, реальная загрузка, доступ твоего аккаунта и результат модели НЕ проверены. В начале S00-02 агент записывает `codex --version`, проверяет конфигурацию установленной версии и доступность модели. При несовместимости фиксирует точный ключ/версию, не подставляет молча неизвестный model ID.
