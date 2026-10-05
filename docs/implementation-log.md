# Журнал реалізації

Цей файл - append-only журнал застосованих змін. Він не замінює `PROJECT_MEMORY.md`: там залишаються продуктові рішення та довгостроковий стан. Сюди потрапляють лише факти після застосування і фактично виконаних перевірок.

## 2026-09-24 - Phase 0: активний quality gate

### Застосовано

- `package.json`: активний browser-контракт FastAPI/Jinja доступний як `npm run test:browser`; `npm run check` запускає Prettier і цей контракт.
- `package.json`: історичний React/Vite-контур збережено під явними командами `npm run legacy:*`; його не видаляли й не вважали перевіркою поточного сайту.
- `.prettierignore`: виключено `.agents/`, `.vscode/` і `server/templates/`.
- `server/templates/` виключено тому, що Prettier інтерпретує Jinja як HTML і пошкоджує вирази на кшталт `locale == 'uk'`. Виявлену синтаксичну помилку в `public_base.html` виправлено.
- Ruff відформатував `deploy/create_env.py` та `deploy/tests/test_deployment.py`.
- `README.md` описує активну browser-перевірку та статус legacy-команд.

### Перевірено

- `npx prettier --check .` - успішно.
- `.local-tools/python/bin/python -m ruff format --check deploy/create_env.py deploy/tests/test_deployment.py` - успішно.
- `GET /uk/` та `GET /en/privacy` без cookie - `200` після ремонту Jinja.
- `npm run check` - успішно: 4/4 browser-сценарії, 64/64 адаптивних перевірки, 32/32 axe-перевірки, 0 JavaScript-помилок і 0 зовнішніх запитів.
- VS Code diagnostics для `package.json`, `.prettierignore`, `server/templates/public_base.html` та `README.md` - без помилок.

### Межі

- Живі Stripe, OAuth, SMTP, Docker/Compose, TLS і production backup/restore цим кроком не перевірялись.
- Файли старого React/Vite-концепту не видалялися.
- Наступний крок Phase 0: огляд і атомарний commit поточного Studio Pulse change set лише після окремого погодження.

## 2026-09-24 - Аудит мертвого коду

### Застосовано

- Видалено `equipmentIds` з `server/static/js/copy.js`: export не мав імпортів або використань в активному застосунку, тестах чи legacy-коді.

### Перевірено

- Ruff `F401` і `F841` для `server/`, `scripts/` та `deploy/` - без невикористаних Python-імпортів і локальних змінних.
- Oxlint для `server/static/js` і `scripts` - без попереджень.
- Пошук `TODO`, `FIXME`, `HACK`, `XXX`, `@deprecated` у активних файлах - без результатів.
- `npm run check` - успішно: 4/4 browser-сценарії, 64/64 адаптивних перевірки, 32/32 axe-перевірки.

### Межі

- `console.log` та `print` у test/report/CLI-скриптах залишено: це очікуваний вивід перевірок, а не debug residue.
- React/Vite-файли не аналізувалися як кандидати на видалення, бо це навмисно збережений historical concept. Їх прибирання потребує окремого погодженого кроку.

## 2026-09-24 - Show Me The Money: протокол і перший review

### Застосовано

- Додано `docs/show-me-the-money-protocol.md` - обов'язковий маршрут skills, phase gates, cadence і місця збереження стану.
- `AGENTS.md` вимагає цього протоколу від усіх агентів; README посилається на протокол і перший report.
- Створено SMTM profile: `~/.smtm/projects/handbalancer-s-studio/profile.json` (`hybrid`, `post_pmf=false`).
- Створено перший append-only checkpoint: `~/.smtm/sessions/handbalancer-s-studio/20260924-202844-mvp-core-and-smtm-protocol.md`.
- Створено evidence-bounded report: `docs/show-me-the-money-report-2026-09-24.md`.

### Висновок

- До live billing потрібні конкретний ICP, Plus fulfillment contract, місткість тренера, unit economics і customer evidence.
- Operator verdict: SHIPPABLE WITH DESCOPE - training-history core + ручний review.
- Customer verdict ще не призначається через недостатньо конкретний ICP.
- Неконтрольований обсяг ручного Plus є existential risk до погодження меж послуги.

## 2026-09-24 - Show Me The Money: уточнення аудиторії та revenue hypothesis

### Зафіксовано зі слів stakeholder

- Аудиторія 18-45 років; напрями: Здоров'я, Еквілібр/handstand, Розтяжка, Базова фізична підготовка.
- Product problem: exercise/repetition tracking, visibility of progress and plateaus, and evidence for changing a program.
- Desired Plus: end-of-week review, knowledge base, video materials, future deep AI analysis; price hypothesis EUR49.99 with 7-day trial.
- Founder target: EUR5-7k net monthly after Irish taxes from home-based coaching.

### SMTM уточнення

- Це product audience, не launch ICP; customer review лишається відкритим до вибору однієї стартової групи.
- EUR5k/EUR7k gross при EUR49.99 потребує щонайменше 101/141 active clients до fees, taxes та coach time. Це сигнал перевірити packaging, capacity й unit economics, не готова фінансова модель.
- AI не можна включати в поточну платну обіцянку до його реалізації та policy.
- Створено checkpoint `20260924-230029-audience-and-revenue-hypothesis.md`; повний update - `docs/show-me-the-money-report-2026-09-24.md`.

## 2026-09-24 - Show Me The Money: cohort capacity і Notes model

### Зафіксовано зі слів stakeholder

- Перший cohort: English-speaking Europe.
- Weekly Plus review: 1 година на клієнта; доступний час засновника: 3-4 години/тиждень.
- Coach Notes закріплені за призначеною вправою; без note порожній блок не показується.
- Success включає progress by direction і >= N completed sessions; N ще відкрите.

### SMTM висновок

- 3-4 години/тиждень при 1 год review означають 3-4 клієнти. EUR49.99 дає EUR149.97-EUR199.96 gross/month і приблизно EUR12.50 gross за delivery-годину до fees/taxes/costs.
- Note і SLA різні: Note - feedback до вправи; SLA - строк delivery/response. Відсутність note не є автоматичним знаком успіху.
- До cohort треба визначити weekly review deadline, N, max pilot cohort і виміряти реальний час review перед рішенням про ціну.
- Створено SMTM checkpoint `20260924-230702-cohort-capacity-and-notes.md`.

## 2026-09-24 - Тарифний delivery contract для Ireland/English cohort

### Застосовано

- Збережено server-owned ціни: Essential EUR19.99, Plus EUR49.99, Pro EUR179.99, Pro+ EUR299.99.
- Plus: план, tracking вправ/підходів/повторів, progress by direction, knowledge base і YouTube learning materials; без гарантованого weekly human review.
- Pro: Plus + weekly practice review до 60 хв, coach Notes на assigned exercises, program adjustments.
- Pro+: Pro + два 30-minute calls/month і personal chat у погоджених межах.
- Прибрано AI/video-analysis promise з Plus; AI не входить у поточну paid delivery.

### Перевірено

- Публічні Ireland benchmarks: online coaching EUR149-150/month, broader online PT EUR150-300/month, in-person PT від EUR55/session і 1:1 Dublin EUR60-100/session. Джерела - SMTM report.
- `npm run check` - успішно: 4/4 browser scenarios, 64/64 layout checks, 32/32 axe checks.

### Межі

- Це конкурентна price/delivery hypothesis, не evidence of willingness-to-pay або profitability.
- Weekly delivery deadline, N success threshold, pilot capacity і actual review time ще потребують виміру.

## 2026-09-29 - Десять макетів робочого місця тренера

### Застосовано

- За дорученням створити 10 макетів і командою `Start implementation` додано лише ізольований пакет [coach-admin](../design-previews/2026-09-29/coach-admin/README.md) та записи стану.
- 10 різних компонувань зі спільними даними/модулями; UA/EN, dark/light, галерея, пошук клієнтів, індивідуальні графіки, історія до підходів, клієнтський вигляд, приватні/видимі нотатки та окреме завершення review.
- Спільні редактори: каталог вправ, архівація без зміни історії, чернетка програми, публікація версії, майбутнє призначення, validation і демонстрація revision conflict.
- 10 desktop і 10 mobile PNG, 20 повносторінкових версій, редактори, галерея, overview, manifest і два фінальні звіти з SHA-256 UI-джерел та основних PNG.
- Локальний сервер http://127.0.0.1:8768/ віддає тільки папку preview. Порт чинного продукту 8000 не змінювався.

### Перевірено

- `.local-tools/node/bin/node --test design-previews/2026-09-29/coach-admin/data.test.mjs`: 6 passed, 0 failed, 0 skipped.
- Oxlint `--deny-warnings --no-ignore` з явними JS/MJS файлами цього пакета: без попереджень. Prettier застосовано тільки до нових preview-файлів; Jinja не форматувався.
- `verify.mjs --matrix`: 10 x 2 мови x 2 теми x 4 ширини = 160 перевірок геометрії; 89 axe; 5 груп поведінки. Завершено 2026-09-29T13:12:11.762Z.
- `verify.mjs --editors-only`: 24 перевірки геометрії та 24 axe. Завершено 2026-09-29T13:12:26.894Z.
- Обидва фінальні звіти: 0 JS-помилок, 0 HTTP-помилок, 0 зовнішніх або product API-запитів. Візуально перевірено макети й експорт, декодування медіа перевіряється автоматично.
- Під час QA виправлено втрату submit-кліку після blur, семантику списку показників, доступну назву мобільної кнопки, overflow таблиці/планшетної навігації та службове skip-link на знімках. Вузькі перевірки виконувались після правок; остання перевіряє Tab -> посилання до вмісту -> main.
- VS Code diagnostics для preview: без помилок.

### Межі та наступний крок

- Це перевірка синтетичного прототипу, не production release, повний аудит WCAG або перевірка серверних дозволів. Реальних клієнтів наразі немає; персональні дані не читалися.
- Відео - концептуальна ілюстрація; YouTube, uploads, AI, БД, auth і платежі не підключені. Календар демонстраційний; редактор має один блок на заняття; повний partial/skipped training engine не реалізовано.
- Чинні `server/`, `db/`, залежності та deploy-конфігурація не змінені. Їхні тести не запускались у цьому завданні; старі результати не видаються за нові. Commit/push не виконувалися; preview залишається Git-ignored.
- Дизайн не обраний. Користувач вибирає 01-10; потім окремо погоджуються точні production-зміни в наявному FastAPI-застосунку.
- Оновлено PROJECT_MEMORY.md і ROADMAP.md. SMTM checkpoint: `20260929-141318-ten-admin-concepts.md`; локальна telemetry фіксує завершення `money-product`, `money-quality` і `money-save` для цього обмеженого обсягу.

## 2026-09-29 - Обрано 02, доопрацювання UX/UI

- Користувач обрав «Три колонки», попросив менше шуму та виправлення кнопок; повідомив про зникнення тексту під hover.
- Причина: `.button:hover:not(:disabled)` перекривав фон `.button.primary`, залишаючи інверсний текст. Primary тепер має явні foreground/background/border для hover/active; disabled не змінюється при hover. Контраст primary hover: 12,54:1 dark, 12,23:1 light.
- Прибрано зайві toolbar controls у 02, дату-дубль, профільний підпис, пояснення під stats і нижній слоган списку. Нейтральні аватари, спокійніші підходи, контекст клієнта/дати збережено. Символ теми більше не будинок; «Програми» називає перехід, а не неправдиво обіцяє створення.
- Додано збереження фокуса за data-action/data атрибутами після rerender, кращі стани іконок/вкладок, мобільні зони від 44 px для перевірених контролів; таблиця даних графіка розкривається в потоці. Новий тест знайшов вузьку вкладку та низький пошук на mobile; виправлено.
- `verify.mjs --controls-only`: 512 вимірів 16 типів контролів у default/hover/active/focus x UA/EN x dark/light x 1440/390; мінімальний контраст 5,33025:1. Додатково focus retention, title/aria-label іконок, touch sizes, disabled invariance, 8 axe. Завершено 16:05:05.175 UTC.
- `verify.mjs --variant 02 --matrix`: 16 геометричних перевірок, 16 axe, 5 груп поведінки; завершено 16:06:13.831 UTC. `--editors-only`: 24/24, завершено 16:06:29.359 UTC. В усіх звітах 0 JS/HTTP/external/API помилок. Один прогін був перерваний закриттям тестового браузера під час axe; повтор без змін коду успішний.
- `node --test .../data.test.mjs`: 6 passed, 0 failed/skipped. Scoped Prettier, Oxlint, VS Code diagnostics успішні. SHA-256 усіх UI-джерел звірено з трьома фінальними звітами. Оновлені знімки 02 та редакторів оглянуті; спільну браузерну вкладку відкрито на 02 й оновлено без reset даних.
- README/manifest, PROJECT_MEMORY.md і ROADMAP.md фіксують вибір 02; SMTM checkpoint `20260929-170645-variant-02-ux-refined.md`. Інші PNG, overview і початковий verification.json залишені історичними, не видаються за повторно перевірені.
- Production/БД/auth/залежності не змінені, commit/push/deploy не виконувались. Це перевірка прототипу в Chrome, не повний WCAG/UX аудит чи дозвіл автоматично впровадити його на сервері.

## 2026-10-05 - Підготовка вузького Git checkpoint

- На доручення commit/push підготовлено пакет coach-admin з обраним 02 і пов'язані документи. Накопичені зміни основного застосунку, БД, CI та локальних налаштувань не включаються; загальне .gitignore не послаблюється.
- Повторний Node test runner: 6 passed, 0 failed/skipped. Oxlint успішний. `verify.mjs --controls-only`: passed, 512 станів і 8 axe; завершено 2026-10-05T11:33:33.528Z. Метадані controls у manifest синхронізовано. Решта матриць - попередні результати 2026-09-29.
- Пакет близько 7 МБ. Перевірка переліку файлів і поширених сигнатур credentials не знайшла приватних ключів, токенів чи файлів локальних даних; це не гарантія відсутності всіх можливих секретів.
- Уточнено межу: адмінка не підключена до основного FastAPI/auth/БД. Сервери попередніх терміналів завершилися. Старий Jinja traceback не є доказом поточного збою: вирази в шаблоні зараз правильні, runtime цим кроком не змінювався.
- Цей запис фіксує підготовку, не успіх push; результат публікації визначається Git і повідомляється після перевірки remote.
