# Внешние gates: реальные вопросы только у границы

Открытые продуктовые/внешние решения не мешают писать локальные contracts и fake-boundary tests. Они **мешают объявлять соответствующую функцию готовой**, подключать реальные данные, запускать расходы/продажи. В `.workflow/state.json` gate начинается pending; approve пишет владелец/интегратор с evidence, не сам исполняющий агент по предположению.

| Gate | Что нужно от владельца / среды | Что блокируется | Что продолжать без этого |
|---|---|---|---|
| G_AUTH_PROVIDERS | Google app (Apple виключено поточним рішенням власника), staging redirects, разрешённый тестовый аккаунт; secrets только dashboard/env | реальный OAuth допуск | gateway, callback tests, UI, каталог |
| G_SMTP | sender domain/provider и реальная доставка; секреты вне чата | production signup/commerce допуск | local Supabase mail test |
| G_STRIPE_TEST | Stripe test project/price IDs/webhook и разрешение test calls | S13-09 внешний roundtrip | projection/inbox/checkout fake tests |
| G_RULES | правила нагрузки, совместимости, допустимые замены | реальное автоматическое планирование без unknown warning | owner CRUD, synthetic deterministic tests |
| G_METHOD | тестовая программа, критерии, правила readiness | настоящая оценка клиента | engine, protocol editor, evidence linking |
| G_VIDEO | разрешённый источник и путь чтения для human/AI, privacy choice | real provider adapter / fetch | ссылки, video versions, access interface |
| G_PRIVACY | retention/deletion, цели processing, third-party consent, scopes private notes | реальная передача/automated retention | opt-out boundary и fake processing tests |
| G_AI_QUALITY | provider/model budget, held-out examples, quality thresholds, rollout decision | реальный autoapply и продажа Plus | наблюдения/proposals/evaluation harness |
| G_PROPLUS | канал чата/звонков, SLA/лимиты/сроки отмены | S15 optional implementation и продажа Pro+ | core Pro workflow |
| G_INFRA_TEST | выделенная staging/restore среда и разрешение rehearsal | restore verification | build/runbook/checker tests |
| G_COMMERCE | налоги/условия/trial/возвраты/что фактически продаём | live Checkout/products enabled | test-mode commerce |
| G_PRODUCTION | конкретный target и отдельное разрешение deploy/cost | production release | локальная разработка полностью |

Наличие ключа не равно разрешению произвольно расходовать средства или отправлять клиентские данные. Missing gate = blocked карточка с причиной, а не новый общий вопрос «что делать дальше?». `roadmap.py next` продолжает доступный independent code.

Gate approval и successful check различаются: G_AUTH_PROVIDERS approved разрешает проверку S17-01, но сам S17-01 остаётся todo до фактического результата. Уровни готовности: code_done, local_verified, external_verified, approved_for_sale. Включение тарифа дополнительно проверяет все обещанные функции, а не только статус gate.

Нет одного обязательного «всё или ничего» публичного релиза: владелец явно утверждает продаваемый набор функций. Нельзя самовольно продавать урезанный Plus под прежним обещанием или считать завершённым весь roadmap при отключённом AI.
