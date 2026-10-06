# Проверяемые вехи, не большие коммиты

| Веха | После задач | Что реально показать |
|---|---|---|
| M0 — среда | S00–S02 | Чистый воспроизводимый запуск, test isolation, light/dark shell |
| M1 — аккаунт | S03–S05 | Local signup/verify/login/profile/onboarding, безопасный paid policy |
| M2 — контент тренера | S06–S07 | Создать упражнение и программу, published immutable tree, private builder |
| M3 — минимальная ценность | S08–S10 | Назначить → выполнить C3 → отчёт → проверить A1, клиент видит feedback |
| M4 — свободный выбор без второго календаря | S11 | Essential replace/add с preview и проверками; coach permissions/requests |
| M5 — оценка | S12 | Тестовая программа проходит через обычный training engine |
| M6 — коммерческий test-mode | S13 + G_STRIPE_TEST | Checkout/trial/webhook/portal в тестовом Stripe, без live продаж |
| M7 — AI-контур | S14 | Fake/shadow evaluated pipeline и защищённый apply, без выдуманной live готовности |
| M8 — сервис и эксплуатация | S15–S16 по gates | Pro+ договорённые каналы, доступность/security, build/restore evidence |
| M9 — согласованный выпуск | S17 | Реальные интеграции, утверждённые тарифы/методика/privacy/infra |

На границе вехи выполнить общий regression и review, но не сливать её 10–20 задач в один большой commit. Для обучения владельца после каждой карточки показывать конкретное изменение; для коммерческой демонстрации — веху целиком. Ни один intermediate checkbox не заменяет реальную проверку внешнего сервиса.
