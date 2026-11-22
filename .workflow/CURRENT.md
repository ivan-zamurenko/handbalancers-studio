# Stripe: S13-08 локальний UI завершено — 2026-11-22

Owner-only subscription/status UI, original-key recovery, Portal button, guarded pages.
53 real DB tests;40 browser cases plus final5 affected regressions; prior62 cabinet/profile
checks overlap. Visual desktop/mobile320/390/1440 both themes; evidence S13-08.
Попередній commit b4b0d74 (06); push відкладений до security follow-up.
Наступне: S13-08a блокує нову підписку при nonterminal старій незалежно від period_end.
Потім09: actual test Checkout/signature/trial/Portal. Тестовий API доступний; точних
чотирьох цін немає, потрібен ізольований test catalog. Live/hosted/deploy не виконані.

## Попередній checkpoint

# Stripe: S13-06 завершено — 2026-11-22

Owner-only Billing Portal API: server customer, fixed return URL, CSRF/Origin,
no-store, test-only provider validation. UI button planned with S13-08.
RED4 SDK +1HTTP; GREEN22 gateway +51 regressions +final1 Portal. Review approved.
Попередній commit043a00f запушено. Наступне: S13-08 purchase/status UI.
Локальний MCP OAuth підтверджено:1 sandbox,0 live; вебплагін не встановлено.
Test API key також уже працює: read-only prices.list success;401 більше не blocker.
Actual test payment, trial lifecycle й real Portal ще не пройдені.
Hosted migrations/live/deploy не дозволені й не виконувалися.

## Попередній checkpoint

# Stripe: S13-05 завершено — 2026-11-22

Один trial на акаунт: reservation до мережі, confirmation тільки після
перевірки Stripe, immutable claimed history. Essential/Plus7 днів з карткою;
Pro/Pro+ без trial. Міграція0015 лише локально. Recovery знаходить загублені
Checkout, повертає URL відкритої сесії; ambiguous outcome не звільняє trial.
Negative release захищений від застарілого customer/listing/discovery.
GREEN169 billing/database/onboarding +26 unit/tooling; Ruff/mypy green.
Read-only review approved після RED/GREEN знайдених гонок.
Evidence S13-05; попередній commit cbe313b. UI не змінено цією карткою.
Наступний крок у Stripe scope: S13-06 owner-only Billing Portal.
Реальний test payment очікує stripe login (наявний test key401). Власнику
показано /opt/homebrew/bin/stripe login. Hosted/live не змінювалися.

## Попередній checkpoint

# Stripe: S13-04 завершено — 2026-11-22

Worker повторно читає актуальний Stripe стан після customer lease, без довгої
DB transaction. Atomic projection/attempt/event, lease fencing,5 retries,
власник через локальний customer+durable Checkout; event time не впорядковує права.
Відомі завислі Checkout перевіряються чергою recovery без starvation/budget reset.
Міграція0014 надає subscription writes тільки trusted studio_worker.
GREEN149 до recovery доповнень; фінальні13 reconciliation і25 gateway/tooling,
Ruff/mypy пройшли. Review знайшов nullable invoice й starvation; RED/GREEN
зафіксовано, follow-up approved. Evidence S13-04; попередній commit40c6d67.
Далі S13-05: один trial на акаунт та verified recovery/release.
Зовнішня перевірка чекає stripe login; hosted/live не змінювалися.

## Попередній checkpoint

# Stripe: S13-03 завершено — 2026-11-22

Durable webhook inbox: raw signature/±300s, testmode only, AES-GCM payload,
worker-only RLS, duplicate event-id,200 тільки після commit. Міграція0013.
RED9 absent module; GREEN71 billing/storage/migration tests. Ruff/mypy green;
read-only review approved. Evidence S13-03. S13-02 commit0dddd44 запушено.
Далі S13-04: current-provider-state reconciliation із durable leases.
Зовнішня перевірка очікує stripe login, попередній test key повернув401.

## Попередній checkpoint

# Stripe: S13-02 завершено — 2026-11-22

S13-02: Checkout intent у БД перед мережею; session/Origin/CSRF/completion,
строгі plan/terms DTO, owner-only status, повтор оригінального key, один active
attempt. Інший key при активній спробі →409. Redirect не надає entitlement.
Міграція0012, вузький studio_worker writer; billing вимкнений за замовчуванням.
132 DB/regression green; після review-fix фінальні13 Checkout green (перетин).
112 unit/tooling green. Read-only review approved. Evidence S13-02.
S13-01 commit0aa8207. Далі S13-03 підписаний durable webhook inbox.
Stripe test credential401; очікуємо stripe login від власника, незалежний код триває.
Хмарних міграцій/live платежів немає.

## Попередній checkpoint

# Stripe: S13-01 завершено — 2026-11-22

За дорученням власника Stripe реалізуємо перед наступними roadmap-етапами.
S13-01: pinned SDK17.1.0/API2026-11-18.endive; серверна перевірка цін,
test-only keys/objects, card-only Checkout, 7-day trial eligibility,
10s timeout/без SDK retries; SDK payload logging вимкнено.
RED16 відсутній модуль; review RED1 витік синтетичного маркера. GREEN17,
раніший full unit103 (перетинається), Ruff/mypy/roadmap green. Review approved.
Evidence: `.workflow/evidence/S13-01.json`. Базовий commit043bc31.
Наступний крок у поточному дорученні — S13-02: durable Checkout.

Архів archive/pre-execution-v4 прочитано; старий runtime не відновлювався.
Наявний CLI test key повернув401; власнику показана команда stripe login.
Тестові платежі дозволені, але зовнішній платіж ще не перевірено.
Live платежів/хмарних міграцій/deploy немає.

## Попередній checkpoint

# S05-04: серверна модель тарифного доступу — 2026-11-22

Уточнення власника 2026-11-22: Stripe підключений; тестові платежі дозволені.
Не називати Stripe непідключеним: у новому runtime ще немає Checkout/webhooks.
Дозвіл збережено в `docs/decisions.md`; G_STRIPE_TEST ще не перевірений.
Коміт S05-04 `a912417` успішно запушений у origin/task/execution-v4.

Завершено S05-04: чиста policy обчислює можливості з довіреної підписки,
поточного часу й готовності функцій. Прострочення/відмова закриває платні дії;
читання власного профілю/історії не залежить від оплати. Plus не надає щотижневої
ручної перевірки; усі можливості за замовчуванням закриті до readiness.

Міграція 0011 додає billing_customers/subscriptions, RLS та обмеження.
0009 із картки вже зайнята preferences; стару історію не змінено. Runtime
може читати лише власну підписку й не може видавати/змінювати доступ. Нових
API/UI/платежів немає. Production writer — майбутній перевірений billing boundary.
Хмарний runner залишається на погодженій 0010; 0011 у хмарі не застосовували.

RED: 53 assertions про відсутній billing-модуль. GREEN: 137 перевірок
(56 нових і 81 регресійна), реальна ізольована PostgreSQL/Supabase через Colima.
Перевірені owner/RLS, заборонені grants, expiry, конкурентні дублікати, свіже
читання після revocation, upgrade/repeat/rollback і захист downgrade.
CI registry: окремий RED 1/8, потім GREEN 8/8. Після підключення таблиць до
перевірки ізоляції повторні 31 migration tests green (перетинаються зі 137).
Ruff/mypy/linear head пройшли. Незалежне read-only review approved.

Evidence: `.workflow/evidence/S05-04.json`. База перед роботою: 03880b6.

Наступна картка — S05-05: спільні серверні auth/role/paid guards.
Stripe/webhooks/hosted 0011/реальний AI цією перевіркою не підтверджені.

## Попередній checkpoint

# S05-03: публічний шлях і тарифи - 2026-11-19

Завершено S05-03. Із тарифів можна перейти до доступної реєстрації без
гостьової анкети. Доступність визначає сервер (email або Google), а не чернетка.
Вибір пакета зберігається; ціни й умови trial незмінні. Вибір не активує
підписку, оплату чи права доступу. Landing/noscript пояснюють поточну готовність.

RED: 5 очікуваних failures, 10 passed. GREEN: 32 browser cases public pages,
guest onboarding і onboarding entry. Read-only review approved.
На запущеному локальному сайті з hosted backend перевірено 16 анонімних
сторінок: 390/1440, light/dark, UK/EN; усі200, без overflow/JS errors.
Вісім переходів із вибраного Pro після reload відкрили форму реєстрації.
Особисто переглянуто вісім screenshots; вони лише в ignored private-evidence.
Акаунти не змінювались; реальний OAuth/оплата цією перевіркою не підтверджені.

Evidence: `.workflow/evidence/S05-03.json`. Базовий30e6f6f запушений.
Наступна картка: S05-04, серверна модель тарифного доступу до Stripe.

## Попередній checkpoint

# Відступи та помилки анкети - 2026-11-19

За проханням власника форма має більше простору: між категоріями28px,
підписом і вибором12px, картками24px desktop/16px mobile. Прибрано конфлікт
із cabinet paragraph reset. Обов'язкові імена/цілі/рівень/дні/тривалість
мають локальні червоні пояснення після Далі/Зберегти; виправлення ховає
повідомлення й прибирає його з accessible description. UK/EN працює наживо.
Optional-поля, API, БД й анімації збереження незмінні.

Mobile відкриває секцію з помилкою, фокусує поле та прокручує групу в центр,
щоб підказка не опинилась під sticky save. Візуально перевірено390/1440,
light/dark, UK/EN на синтетичних даних, 0browsererrors/overflow.

RED5 початкових сценаріїв; окремі RED для accessible-description після
корекції та перекриття hint панеллю. GREEN34browsercases; після останнього
scrollfix18affectedcases (перетинаються, не52унікальних). Reviewapproved.
Evidence: `.workflow/evidence/profile-validation-2026-11-19.json`.
Screenshots лише в ігнорованій private-evidence/profile-validation-2026-11-19.
Фізична телефонна клавіатура/hosted save не перевірялися в цій UI-правці.
Базовий cf165d3 запушений. Наступний roadmapкрок: S05-03.

## Попередній checkpoint

# Автономна перевірка онбордингу - 2026-11-19

Завершено погоджений крок 2 без участі власника: створено синтетичні акаунти
через реєстрацію в ізольованій локальній Supabase, підтверджено email через
локальну пошту, перевірено незавершений онбординг, save/reload і повторний
вхід у новому браузерному контексті. Реальні Auth/DB/API, без підміни відповідей
у повному сценарії. Hosted-акаунт власника не змінювався.

Повний сценарій: 68 перевірок, 15 станів/знімків, 0 JS помилок. Реальний offline
submit показує анімацію помилки, зберігає введення; після відновлення мережі
retry зберігає дані без зайвої ревізії. Missing/stale CSRF403, actor/role injection422,
stale questionnaire409. Завершена анкета веде на dashboard після нового входу.

Знайдено й виправлено: ранній вибір теми губився під час GET preferences;
поле теми/мобільний підсумок не слідували за header; повільне завантаження
профілю могло відновити старе значення. RED відтворено окремо: 3+2+1 failures.
GREEN: 73 browser cases до останньої правки профілю; 20 affected cases після
неї (перетинаються з 73); 12 JS tests. Read-only review approved.

Після останньої правки: 12 реальних сторінок/розмірів/тем успішні, без overflow
і JS errors; select відповідає темі. Особисто переглянуто desktop/mobile,
light/dark, початкові кроки, результат успіху й помилки. Приватні screenshots,
логіни та replay scripts у private-evidence/onboarding-roundtrip-2026-11-19;
credentials0600, директорія0700, Git їх не відстежує.

Evidence: `.workflow/evidence/onboarding-roundtrip-2026-11-19.json`.
Базовий коміт 7816e9e запушений; цей follow-up має окремий commit.
Це локальна перевірка: нова hosted email registration/Google OAuth і hosted
save/relogin не перевірялися тут. Схема, провайдери, ціни незмінні.
Наступний крок: S05-03, погоджені публічні сторінки й тарифи.

## Попередній checkpoint

# Відновлення доступу до кабінету — 2026-11-19

Завершено перший погоджений крок: відтворені й виправлені збої повторного
використання закритого DB-з’єднання та необроблена помилка фінального читання
сесії. Обидва runtime-пули мають pre-ping; final session read повертає
контрольований503 при тимчасовому збої без logout/replay/витоку даних.
Схема, права, анкета, UI та провайдери незмінні. Це follow-up S03-06.

RED: 5 нових сценаріїв впали за очікуваною причиною; GREEN: ті самі5 пройшли.
Affected regression: 203 passed + 23 після виправлення PATH для вже встановленого
локального Supabase CLI; загалом226 різних сценаріїв, без skip. Початкові
collection/setup errors записані в evidence. Read-only review approved.

Hosted після перезапуску локального сервера: session200/authenticated/complete,
root→dashboard; overview/progress/profile200 на1440/390; шість read-only
session checks200, account writes0, browser/server errors0. Особисто переглянуто
шість screenshots, приватні поля замасковані; private-evidence не tracked.
Старий503 не має збереженої причини: не називати його точну причину доведеною.

Evidence: `.workflow/evidence/session-db-recovery-2026-11-19.json`.
Базовий коміт dbdb8e9 запушений. Наступний крок — повний сценарій
вхід → онбординг/кабінет → збереження → повторний вхід; потім S05-03.
Справжній hosted save/relogin у цьому read-only кроці не перевірявся.

## Попередній checkpoint

# Порожній прогрес — 2026-11-19

/progress має новий empty-state: одноразова анімація сходинок до зеленої
крапки, пояснення й «До огляду». Reduced motion — статично. Порожні метрики,
heatmap і вкладки з цієї сторінки прибрано; невикористаний JS/CSS видалено.
Dashboard/анкета/анімація збереження/схема/API/серверні guards незмінні.

Локально: 11 browser cases кабінету + 9 профілю green; додаткові 4 geometry
перевірки для коректного знімка кінцевої теми перекривають профільний suite.
Особисто переглянуто progress320/390/1440 в обох темах, overview/profile390/1440,
український progress desktop і кадри анімації 0/1400/3450 мс. Review approved.
Evidence: `.workflow/evidence/progress-empty-2026-11-19.json`.

Hosted повторна перевірка env_blocked: /progress повернув503 до рендеру
сторінки двічі; причина auth/DB guard ще не встановлена. Не називати hosted
перевірку успішною. Наступна дія — діагностика цього503; після неї S05-03.
Приватні скріншоти лишаються поза Git. Базовий коміт 6d0eb12 запушений.

## Попередній checkpoint

# Корекція геометрії кабінету — 2026-11-19

Виправлено за скріншотом власника: знак h. зліва, назва справа, спільний
вертикальний центр і центрування групи в sidebar. Загальне SVG-правило
звужено до header/workout art: воно перебивало приховування desktop-chevron
профілю та роздувало legend до 602 px. Mobile sticky save узгоджено з
16 px відступом кабінету (раніше виходив на 2 px за екран).

15 браузерних перевірок пройшли: кабінет, форма/save feedback, геометрія
390/1440 у двох темах. Read-only review схвалено. У сесії власника
перевірено центр логотипа (зсув 0 px), legend 20 px, desktop-chevron hidden;
account writes = 0. Evidence: `.workflow/evidence/cabinet-alignment-2026-11-19.json`.
Базовий коміт 517542d запушений. Приватні файли й screenshots поза Git.
Наступна картка S05-03; SQL/API/анімації не змінені.

## Попередній checkpoint

# Поточний checkpoint — окремий кабінет, 2026-11-19

Погоджене уточнення S05-02: C1-кабінет має власні «Огляд / Прогрес / Профіль»,
бічне меню на desktop і бургер на телефоні. «Сьогодні» прибрано з navbar;
«Напрями / Методика / Тарифи» залишені гостьовому шляху. Root/plans для
підтвердженої сесії перенаправляють за completion; /progress має той самий
серверний guard, що /dashboard. Публічні сторінки доступні при збої auth,
але protected views лишаються fail-closed.

Огляд: блок поточного заняття, показники, карта регулярності. Прогрес:
п’ять доступних із клавіатури вкладок. Даних тренувань ще немає: тільки
чесні порожні стани; це не реалізація тренувального рушія чи аналітики S08–S10.
Форма й погоджені save-анімації залишилися в кабінеті. Нових міграцій немає.

Локально: isolated DB 9; HTTP/auth 61; JS 61; широкий browser run 51 passed
і одна знайдена помилка stale-cookie. Після виправлення фінальний affected
subset 24 passed (перекриває попередній run); уточнення мобільних вкладок
перевірено окремо: 6 passed. Подробиці, RED/GREEN й review у
`.workflow/evidence/member-cabinet-2026-11-19.json`.

Hosted read-only у сесії власника: root → dashboard, session complete,
progress 200 і вкладки працюють, profile 200 і форма завантажується;
жодного account write. Локальний кабінет залишено відкритим у Chromium.
Приватні CV/кар’єрні/бізнес-матеріали й скріншоти поза Git.
Базовий checkpoint перед цією зміною: 65dad6f, запушений у task/execution-v4.
Наступна roadmap-картка S05-03 — звірка публічного шляху й тарифів.

## Попередній checkpoint

# Поточний checkpoint — завершення онбордингу й мова, 2026-11-19

Виконано погоджене уточнення S05-02: `/dashboard` перевіряє сесію й наявність
завершеної анкети через БД/RLS. Незавершена → `/profile`, завершена → кабінет;
повторний Google/email вхід не повторює завершений онбординг. Помилка перевірки
не відкриває кабінет. Session completion може бути null (невідомий), не false.
Публічна головна/тарифи доступні без покупки. Сьогоднішнє заняття ще не реалізоване:
кабінет показує чесний порожній стан до S08–S09.

UA/EN і тема зберігають DOM форми, вибір і активний крок. Новий default після
email/Google-входу та першого успішного save — dashboard. Схема/ціни незмінні.
Браузерна регресія: 81 passed, 4 старих очікування очищення пароля при reload
переглянуто за новим контрактом; фінальний affected subset 32 passed, пароль
лише в DOM, не storage. HTTP/auth 61, JS 61, DB regression 41 + фінальні entry 7
(частково перекриваються); Ruff/mypy runtime/нового тесту пройшли.
У спільній OAuth-фікстурі є 8 попередніх lint-зауважень (такі самі в HEAD). Read-only review схвалив після
виправлень перекладу тривалості/title/мови OAuth.

Live після входу власника: /api/session = 200, authenticated=true,
setup_required=false; /dashboard = 200. Прямий /onboarding → 303 → dashboard,
анкета не показується. UA/EN без перезавантаження підтверджено. Записів у профіль
чи анкету не було. Перевірено наявний завершений акаунт із хмарною БД; сценарій
нової реєстрації/першого Google-входу окремо не виконувався.
Реалізація f54e0f3 запушена в origin/task/execution-v4.
Мобільний гостьовий UI перевірено; скріншоти лише private-evidence, поза Git.
Докази: `.workflow/evidence/onboarding-entry-2026-11-19.json`.
Наступна roadmap-картка: S05-03. Нових міграцій немає.

## Попередній checkpoint S05-02

# Поточний checkpoint — S05-02 гостьовий онбординг, 2026-11-19

## S05-02 завершено локально; hosted save підтверджено

Додано /onboarding: два кроки (цілі/рівень → графік), перехід до тарифів і
реєстрації. POST /api/onboarding/draft перевіряє allowlist і строгий Origin;
це валідація, не запис у БД. Несекретні відповіді зберігаються в поточній вкладці
до 24 годин; після підтвердження сесії прив’язуються до namespace акаунта.
Порожня анкета підставляється для перегляду; наявна вимагає явного «Підставити»;
запис лише через Save із серверною revision. Logout очищає прив’язану чернетку.
Під час запиту поля заблоковані; помилка повертає керування без втрати вибору.
Схема БД й погоджені ціни не змінені. Оплата/AI ще недоступні.

Перевірки: 64 e2e, 61 JS, 61 HTTP/auth, 16 isolated DB; Ruff/mypy пройшли.
Read-only review: виправлено втрату нового вибору під час pending POST, схвалено.
Реальна сесія власника: PATCH profile = 200, PUT onboarding = 200; успішна
анімація shift → hold → paint → result; після reload відповіді незмінні,
ревізія збільшилась на один. Жодних синтетичних відповідей у цьому hosted smoke.
Гостьовий Google/email roundtrip поки перевірений лише через synthetic auth
boundary у браузерних тестах; фізичний телефон/Safari не перевірені.
Докази: `.workflow/evidence/S05-02.json`. Приватні файли лишаються поза Git.
Наступна картка: S05-03 (звірка публічного шляху й тарифів).

## Попередній checkpoint — S05-01, 2026-11-18

Профіль = форма з анкетою (цілі, рівень, 1–3 дні, час, 30/45/60/90 хв, рік народження/зріст/вага
необов’язково). Обмеження однакові в UI/API/БД; міграція 0010; setup_required → одноразовий
перехід у профіль. Хмара: 0010 застосовано власником 2026-11-18, незалежна read-only перевірка таблиці/RLS пройшла. Докази: `.workflow/evidence/S05-01.json`.

## Хмарна міграція 0010 завершена — 2026-11-18

Власник дозволив застосування та виконав підготовлену команду з прихованим
паролем postgres. Результат: Applied migration upgrade to Alembic 0010;
ownership and RLS verified. Baseline 0006 незмінний; новий approved target 0010.
Незалежна read-only перевірка через runtime-з’єднання: таблиця анкети існує,
власник postgres, RLS увімкнено, три own-row політики, anon/authenticated/
studio_auth_runtime/studio_worker без доступу, без user context записи не видно.
Локально: 42 DB тести пройшли (0009→0010, повторний запуск, збереження даних,
відмова при drift політик/дозволів, API анкети), Ruff і mypy пройшли.
Хмарний gate 0010 закрито. Повний ручний save через браузер у хмару ще не перевірений.
Докази: `.workflow/evidence/cloud-0010-2026-11-18.json`.
Наступний roadmap-крок залишається S05-02.

## Анімації та мобільний UX закомічено й запушено — 2026-11-18

Анімації вже підключені: member/profile.html → profile.js → playSaveFeedback,
після відповіді на submit. Runtime — SVG/JS/CSS у server/static, GIF/відео не потрібні.
Погоджені зміни анімацій, мобільної форми й меню перевірено разом:
56 JS тестів + 56 браузерних сценаріїв пройшли, read-only review без блокерів.
Усі 323 файли private-evidence ігноруються, відстежуваних приватних файлів немає.
Коміт 6e89eb2 запушено в origin/task/execution-v4 явним списком файлів.
Ручне хмарне збереження ще не перевірене; міграцію 0010 застосовано (див. вище).
Докази: `.workflow/evidence/save-feedback-delivery-2026-11-18.json`.

## Погоджені анімації збереження — 2026-11-18

Залишено поточні реалізовані варіанти:
- Успіх: виштовхування на опорному плечі, утримання 1 с,
  контурний водоворот у зелене коло з білою галкою та «Збережено» (v3).
- Помилка: втрата балансу, водоворот ще під час падіння до приземлення,
  червоне коло з білим хрестиком та «Виникла помилка» (v4).

Власник погодив обидва варіанти й доручив прибрати непотрібні.
Погоджені записи: `private-evidence/save-feedback-approved/success.mp4`
і `private-evidence/save-feedback-approved/error.mp4` (синтетичні API, поза Git).
Видалено застарілі/дубльовані медіафайли, старі capture-скрипти,
окрему сторінку tools/previews/save-feedback та її невикористовуваний previewPose.
Мобільні UI-знімки й історію RED/GREEN збережено; шляхи в evidence актуалізовано.
Докази руху: `.workflow/evidence/save-motion-2026-11-18-v3.json`,
`.workflow/evidence/save-motion-2026-11-18-v4.json`.
Анімації лише після відповіді на відправку форми. Хмарний gate 0010 закрито (див. вище).
Очищення не змінює погоджені рухи; 5/5 браузерних перевірок форми пройшли.
Докази: `.workflow/evidence/save-feedback-cleanup-2026-11-18.json`. Commit/push не виконували.

## UX-виправлення за дорученням власника — 2026-11-18

Локально перероблено падіння (контакт ноги → згинання коліна → відрив кисті → бік),
анімація лише після відповіді сервера, секундний hold успіху, пропуск/reduced-motion,
повернення фокусу. На телефоні бургер-меню, покрокове перше заповнення та акордеон
редагування; великі radio-варіанти, нижні кнопки, числові поля по одному в ряд.
Виправлено конфлікт inert при відкритті меню під час запиту.
Перевірено 56 браузерних сценаріїв (55/56 у загальному запуску, після виправлення
гонки тесту logout — 8/8 його suite), 50 JS тестів. Знімки 320/390/1440, обидві теми,
UI-знімки — в ігнорованій `private-evidence/save-mobile-2026-11-18/`.
Старі записи анімацій із цієї папки видалено після погодження фінальних варіантів. Не перевірено фізичний телефон/Safari
та hosted збереження з 0010. Докази: `.workflow/evidence/save-mobile-2026-11-18.json`.
Наявні на початку незакомічені зміни меню збережено й допрацьовано; коміту/push
цього доручення не робили. Наступний roadmap-крок залишається S05-02.

## Попередньо — макет кабінету (профіль + прогрес), 2026-11-16

Власник визначив зміст профілю й метрики прогресу (`docs/decisions.md`,
«Профіль і прогрес»), включно з heat map регулярності як у GitHub. Зроблено
синтетичний макет у стилі C1: `tools/previews/cabinet/{profile,progress}.html`
(390/1440, обидві теми, без помилок/переповнення). Чекає погодження власника;
логіку не реалізовано. Сервер 8000 перезапущено на поточному коді (власник
дозволив); /api/me у хмарі = 503 (немає DATABASE_URL і міграцій 0008/0009).

## Хмарна міграція 0007–0009 (дозвіл власника 2026-11-17)

`tools/migrate_cloud.py`: APPROVED_CLOUD_REVISION=0009 (adoption лишається 0006);
тести: прийнята база 0006 → 0009 з незмінними даними; DB suites зелені.
Web-логін тепер відхиляється, якщо ширший за studio_web (UnsafeWebRole).
SQL для логіна: `supabase/web-login.sql`; інструкція: `.workflow/REGISTRATION_BASELINE.md`.
Статус: застосовано власником; хмара на 0009, studio_web_app працює, /api/me = 401 без входу (раніше 503).

## Наступний крок

Після погодження макета: розкласти профіль/прогрес на картки roadmap
(вік/зріст/вага — G_PRIVACY; метрики залежать від S08/S09 тренувальних фактів).

## Попередньо — S04-06 profile & preferences

S04-06 виконано локально: сторінка /profile (ім’я, прізвище, мова, тема),
API /api/me/profile і /api/me/preferences (ревізія, 409 при конфлікті) від імені
studio_web під RLS; міграція 0009 (studio.user_preferences). Тема акаунта
зберігається під studio:account:<id>:theme і очищається при виході.
Review знайшов 2 гонки теми на клієнті — виправлено й перевірено в браузері.
У хмарі: DATABASE_URL не налаштовано, 0008/0009 не застосовано → /api/me = 503.
Докази: `.workflow/evidence/S04-06.json`.

## Попередньо — S04-05 coach bootstrap

S04-05 виконано локально: роль coach видає лише власник CLI
`python -m studio.accounts.cli grant-coach|revoke-coach <auth_user_id> --actor <ім'я>`
(операторський DB-доступ, не email), з аудитом у новій таблиці
`studio_private.audit_events` (міграція 0008, RLS, без грантів runtime-ролям).
RED 4→GREEN 4; check_migrations усі набори зелені; review clear.
У хмарній БД 0008 НЕ застосовано — потрібен дозвіл власника.
Докази: `.workflow/evidence/S04-05.json`.

## Попередньо — S04-04 identity linking

S04-04 виконано локально: профіль = auth UUID, без злиття за email. 4 тести
(`server/tests/security/accounts/test_identity_linking.py`), 2 ключові мутації
зловлено, regression 127. Код не змінювався. Докази: `.workflow/evidence/S04-04.json`.
Власник 2026-11-16: лише необхідні й критичні тести, без надмірності.

## Попередньо — Apple видалено, S04-03 skipped

За рішенням власника Apple-вхід видалено з коду (allowlist лише google, налаштування
oauth_apple_enabled прибрано, docs оновлено); S04-03 — skipped, S04-04 тепер залежить
від S04-02. CHECK у БД (0004) ще допускає 'apple' — застосунок не записує.
RED→GREEN; checks.py exit 0; DB suites 202. Докази: `.workflow/evidence/S04-03.json`.
Причина й правила для агентів: `docs/adr/apple-sign-in-removed.md` (посилання також в AGENTS.md).

## Попередньо — S04-02 oauth callback

S04-02 виконано локально (IMPLEMENTED_LOCAL). Поведінка callback уже була з S04-01a;
додано HTTP-тести `server/tests/security/accounts/test_oauth_callback.py`
(DB-suite замість contracts/, бо contracts у CI без БД): replay, чужий браузер,
скасування з повторною спробою, профіль один раз, redirect лише на дозволений шлях,
code не в серверних логах. 7 GREEN; DB suites 201; 6 мутацій зловлено; review —
перевірку логів посилено. Докази: `.workflow/evidence/S04-02.json`.

## Попередньо — S04-01 oauth attempt

S04-01 виконано локально (IMPLEMENTED_LOCAL). Поведінку вже реалізувала S04-01a,
тому RED поведінки немає (чесно записано); додано тести картки
`server/tests/security/accounts/test_oauth_attempt.py`: PKCE verifier на кожну
спробу, allowlist return_to і провайдерів, паралельні старти без змішування.
GREEN 15; regression security+oauth+contracts 209; 6 мутацій зловлено; review —
2 слабкі асерти виправлено. Докази: `.workflow/evidence/S04-01.json`.

## CI-ремонт (2026-11-16)

CI був червоний з 4b4c4b4: (1) pip-audit — CVE-2026-126360 у opentelemetry-api
1.45.1 → оновлено до 1.45.2 у uv.lock; (2) з 7544ace DB-job — тест відновлення
шукав лист за українською темою; тепер тема береться з supabase/config.toml.
Також `server/tests/security/accounts` (S04-01) додано в DB_SUITES CI.
Локально: baseline checks.py зелений; DB suites 179 passed; tools/tests 68.

## Попередньо — S03-11 auth local e2e

S03-11 виконано локально (IMPLEMENTED_LOCAL, live_verified=false).
Наскрізний gate на реальному local Supabase test stack без моків:
register → код лише з loopback Mailpit (лист видаляється в catcher) →
verify → session → logout (CSRF) → login. Профіль пов'язаний з реальним
managed `auth.users` (validated FK), повторний login не створює профіль,
після logout стара cookie дає 401, а upstream refresh token відхиляється.

Нове: `tools/local_auth_fixture.py`, `server/tests/integration/auth/test_auth_local_e2e.py`.
RED: ImportError відсутньої фікстури. GREEN: 4 passed; regression
`server/tests/integration/auth`: 100 passed; мутаційна перевірка ловить
невидалений лист і відсутній auth user. Review — clear.
Докази: `.workflow/evidence/S03-11.json`.

Запуск: Colima `studio-s01`, `DOCKER_HOST=unix://$HOME/.colima/studio-s01/docker.sock
DOCKER_CONTEXT=default .venv/bin/python -m tools.local_stack test .venv/bin/python -m pytest …`.

Не підтверджено: hosted email/SMTP, Google OAuth live, браузерний шлях цього gate.
Hosted OTP/recovery, key rotation, cloud 0007 та provider gates лишаються відкритими.
Попередній checkpoint (мобільна навігація, `9ff4f3d`): `history/2026-11-08-mobile-navigation.md`.

## Live-перевірка hosted dev (2026-11-16)

Google-вхід працює (з боку власника). Лист на новий аліас доставлено вбудованим
SMTP Supabase, але hosted-шаблон надсилає посилання, а не 6-значний код —
підтвердження на hosted неможливе, доки шаблон не змінено (на поточному плані
редагування недоступне). Для наявного email лист не надсилається навмисно;
на сторінці коду додано нейтральну підказку.
Потім: домен handbalancers.com (Cloudflare), Resend SMTP `no-reply@mail.handbalancers.com`,
англійські шаблони в дизайні застосунку, OTP 6 цифр. Власник підтвердив: лист
реєстрації й скидання пароля у «Вхідних», обидва сценарії пройдені. DMARC p=none опубліковано. Докази:
`.workflow/evidence/live-auth-check-2026-11-16.json`. G_SMTP/G_AUTH_PROVIDERS — pending.

## Наступний крок

S05-01 `onboarding_model` — Сохранить анкету без медицинского scoring (`tools/roadmap.py next`).
