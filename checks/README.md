# Что проверено при выдаче v4

16 unit tests read-only roadmap utility: сначала RED (utility отсутствовал), затем GREEN после реализации. Это тесты инструмента выполнения roadmap, **не тесты приложения**. Логи сохранены как workflow-red.txt / workflow-green.txt.

5 существующих тестов reference theme controller повторно запущены Node. Это проверка приложенного дизайнерского reference-модуля; новый production ThemeController ещё предстоит написать TDD по S02-03.

11 Chromium DOM-проверок документации: навигация, поиск task, themes, 390/1440 overflow и menu. Для просмотра использовался in-memory HTML. Внешняя HTTP/file navigation в данной среде заблокирована policy; cross-reload localStorage и открытие файла на компьютере владельца этим запуском не доказаны. Не менялись browser security policies.

Структурно проверены 134 task cards /18 stages/552 acceptance scenarios, отсутствие циклов и пропавших prerequisites, начальный state, JSON/TOML syntax, 477 current HTML links/anchors и все 12 выбранных PNG. Исторические relative links v3 не считаются текущей навигацией.

Skill прошёл официальный доступный skill-creator validator/package script. Config Codex сверена с текущей официальной документацией и разобрана TOML-парсером. Здесь нет установленного Codex CLI/Docker и нет product backend/SQL, поэтому реальное выполнение config, Supabase, OAuth, Stripe и AI не проверялось. Никакой live push/deploy не выполнялся.

Сами acceptance scenarios ещё не являются написанными executable application tests: их пишет следующий агент **до** соответствующего runtime-кода. В state все application tasks TODO. Это принципиальная граница доказательств.
