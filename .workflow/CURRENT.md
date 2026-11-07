# Поточний checkpoint — S03-07 завершено локально

2026-11-07: вихід відкликає local session до мережі, навіть якщо encrypted tokens
пошкоджені або протерміновані. Upstream sign-out має 5-секундний загальний timeout
і scope=local; інші пристрої лишаються активними. 204 підтверджує local logout,
а результат upstream відокремлений. CSRF/Origin обов'язкові; повтор із тим самим
cookie/CSRF безпечний, старий cookie відхиляється.

Браузер очищає поточний account draft/cache namespace після підтвердженого виходу,
зберігає guest preferences й не дозволяє застарілому snapshot відновити стан.
Рішення/межі: `docs/adr/S03-07-logout.md`; докази: `.workflow/evidence/S03-07.json`.
Перевірки: 64 auth integration, 104 unit/contracts/security, 24 browser GREEN;
Ruff/Mypy GREEN, read-only review без блокувальних зауважень. Реальний LOCAL
Supabase sign-out та збереження другої upstream session перевірені.

Перший широкий auth run мав одиничний401 у незміненому тесті повторного password
login (63passed/1failed); ізольований повтор і повний повтор64passed без правок.
Причину не встановлено, очікування/перевірки не послаблювали. Це записано в evidence.
Попередній fcfbd33 pushed, CI42425676793 baseline/database success.

Хмарна БД досі на0006; застосування0007 із S03-06 та hosted smoke/deploy лишаються
окремими кроками. S03-07 не змінює схему. Google/email увімкнені; Apple вимкнено.
Видалення docs та інші сторонні файли не включати в коміт; roadmap validator
пройшов на snapshot індексу: 142 картки, 0 помилок. Гілка task/execution-v4.
Наступна картка: S03-08. Commit/push/CI цього checkpoint перевірити після коміту.

## Історичний checkpoint S03-06

### S03-06 завершено локально

2026-11-07: S03-06 відновлено за запитом власника й реалізовано. Refresh має
30-секундне резервування в БД, захист від запису застарілим запитом, атомарну
заміну encrypted access/refresh та expiry, bounded timeout і recovery. Вихід
під час refresh не відновлює сесію. Нові локальні сесії мають фіксований строк
7 днів; access expiry окремий, refresh не продовжує local lifetime.

Перевірено: 59 database + 20 RLS/security + 56 auth (включно з 21 refresh),
99 unit/contracts/security, 8 migration-tooling tests; Ruff/Mypy GREEN.
Реальний LOCAL Supabase refresh/JWT пройшов. Read-only review завершено;
знайдений крайовий випадок oversized response виправлено через RED/GREEN.
Докази: `.workflow/evidence/S03-06.json`; рішення: `docs/adr/S03-06-session-refresh.md`.

Alembic head локального коду — 0007: тільки UPDATE grants на чотири існуючі
колонки private sessions. Хмарна БД лишається на підтвердженому 0006.
До використання нового runtime у хмарі потрібне окреме застосування/перевірка
0007; хмарний refresh і deploy не виконувалися. `tools.migrate_cloud` досі
навмисно застосовує лише 0006. Існуючі прострочені сесії потребують нового входу.

Roadmap validator у робочому дереві бачить попередні видалення власником docs;
їх не відновлювали й не включали в коміт. Окремий snapshot індексу пройшов
roadmap validation: 142 картки, 0 помилок; next=S03-07.
Google та email/password залишаються єдиними активними способами входу; Apple
вимкнено, кнопку видалено попереднім комітом a8d9a29.

Наступна картка: S03-07 — негайний локальний вихід. Зупинка на межі S03-06.
Гілка task/execution-v4; commit/push status перевірити після коміту.

## Історичний checkpoint до відновлення S03-06

### Хмарну БД прийнято під керування Alembic 0006

2026-11-07, остаточне рішення власника: Apple OAuth не підключаємо; залишаємо
Google та email/password через Supabase Auth. Apple виключено з поточного обсягу,
а не залишено в очікуванні платного членства. Backend-підтримка лишається вимкненою.
Перевірено локальні прапорці: OAUTH_GOOGLE_ENABLED=true, AUTH_EMAIL_ENABLED=true,
OAUTH_APPLE_ENABLED=false. Apple не є блокером для продовження поточного roadmap;
історичні вимоги Apple застосовувати лише після нового рішення власника.

За окремим запитом власника кнопку Apple видалено з форми входу. Google та
email/password залишилися. Очікування наявного browser-тесту змінено відповідно
до нового рішення: Apple відсутня навіть коли fixture оголошує обох провайдерів;
перевірка блокування кнопки під час запиту тепер стосується Google.
RED: `playwright test tests/e2e/oauth-ui.spec.js --max-failures=1` — тест отримав
1 кнопку Apple замість 0. GREEN: `playwright test tests/e2e/login-form.spec.js
tests/e2e/oauth-ui.spec.js` — 16 passed. Реальний OAuth повторно не перевіряли;
браузерний тест перевіряє інтерфейс і відновлення після змодельованої помилки.
Наступна roadmap-картка лишається S03-06; її реалізацію ця UI-зміна не починає.

2026-10-21: власник успішно виконав `tools.migrate_cloud --adopt-bootstrap --apply`.
Результат після COMMIT: `Applied baseline adoption to Alembic 0006; ownership and RLS verified.`
Це перевірене прийняття вже створеної SQL bootstrap схеми, а не повторний запуск
історичних CREATE. Таблиці та дані не відтворювалися.

Незалежна post-commit перевірка через обмежене studio_app підключення:
- product schema відповідає еталону 0006;
- журнал studio.alembic_version існує, owner postgres, RLS увімкнений;
- studio_app, studio_auth_runtime, anon та authenticated не мають DML на журнал;
- обидва глобальні defaults postgres для майбутніх функцій/типів існують без PUBLIC;
- studio_app і TLS працюють, архівна схема studio_legacy_20261020 присутня.
Revision 0006 підтверджена повідомленням операторського скрипта; runtime навмисно
не читає рядки журналу. Managed-схеми перевірені самим скриптом до COMMIT.

Коміти запушено в origin/task/execution-v4:
- 955a773 — verified baseline adoption;
- 04b0373 — безпечна діагностика підключення та виправлення newline для CI.
Перевірки: 89 DB checks, follow-up 60 unit + 39 contract/security tests;
Ruff/format/mypy і read-only review пройшли. CI39642149720: baseline passed,
database job ще виконувався на момент checkpoint.

Попередня перешкода була `authentication_rejected` до початку SQL, а не помилка
міграцій. Власник обрав скидання пароля postgres й потім повідомив успішний запуск.
Пароль studio_app та .env.local агент не змінював, секретів не зберігав.
Evidence: `.workflow/evidence/registration-baseline.json`.
Інструкція: `.workflow/REGISTRATION_BASELINE.md`. Bootstrap повторно не запускати;
наступні зміни БД оформлювати новими Alembic revisions.

Наступна roadmap-картка — S03-06 (refresh singleflight і atomic token swap).
Ця робота завершила DB adoption; S03-06 та розширення refresh grants ще не поновлені.
Її RED-тести/evidence лишаються локальними й поза комітами. Видалення docs та інші
зміни власника збережені.

Нижче історичний checkpoint. Старі твердження про неперевірені runtime/signup/Google
не чинні: runtime, signup через лист-посилання, password і Google login перевірені.
Cloud OTP ще не перевірений.

## Попередній checkpoint — реєстраційна БД та UI

Закомічено й запушено в origin/task/execution-v4 (2026-10-21):
- `775287c` feat(db): хмарна реєстраційна БД прямим SQL, без міграцій
- `c7f3f65` feat(ui): іконкові кнопки входу, анімований перемикач теми, стабільна шапка
Не включено у коміт навмисно: RED-тести S03-06 і його evidence; видалення старих
`docs/*` (зміни власника); локальні tooling-файли `.claude/`, `.vscode/`,
`copilot-instructions.md`, `docs/copilot/`, `skills-lock.json`, `.agents/skills/*`.

2026-10-21: власник визначив пріоритетом налаштувати БД для реєстрації напряму,
без запуску Alembic/Supabase migrations. `supabase/bootstrap-registration.sql`
виконано через Supabase SQL API у наявному проєкті. Створено `studio.users`,
`studio_private.web_sessions`, `auth_attempts`, `auth_rate_limits` і три вузькі
функції provisioning/profile. Перевірено FK до `auth.users`, RLS на всіх таблицях,
відсутність DML у anon/authenticated, grants функцій лише для `studio_auth_runtime`;
усі нові таблиці порожні. Legacy archive не змінений; migration ledger лишився
на попередніх чотирьох записах.

Runtime-підключення готове: створено окрему роль `studio_app` (LOGIN, INHERIT,
без superuser/createrole/bypassrls), що успадковує лише `studio_auth_runtime`.
Перевірено реальним підключенням через session pooler: current_user=studio_app,
TLS увімкнено, виклик приватних функцій дозволений, CREATE у studio/studio_private
заборонений. `create_app` з цим конфігом піднімає auth/verification service і
відкриває обмежену транзакцію. Supabase Auth: signup дозволений, email provider
увімкнений, mailer_autoconfirm=false (потрібне підтвердження листом).

Реєстрація перевірена на живій хмарній БД (2026-10-21): signup → 202,
справжній лист підтвердження, після підтвердження password login → 200.
Створено 1 профіль (role=member, зв'язок із auth.users), 1 активну сесію;
/api/session повертає authenticated. У БД: tokens зашифровані, JWT відкритим текстом
відсутній, cookie зберігається лише як hash, rate-limit buckets працюють.
Хмарний шаблон листа — стандартний із посиланням, тому OTP-ендпоінт /api/auth/verify-email
на хмарі ще не використовувався; для коду потрібно змінити шаблон у Dashboard
на {{ .Token }}. Сторінки реєстрації/входу в UI — окремі картки roadmap.

Google OAuth підключено й перевірено живим входом (2026-10-21): кнопка на /login →
згода Google → redirect на /plans. Supabase прив'язав google-identity до того самого
користувача за підтвердженою поштою: 1 auth user, 2 providers, 1 профіль (без дубля),
2 активні сесії, PKCE attempt спожитий. OAUTH_GOOGLE_ENABLED=true.
Важлива пастка: у Google Cloud аудиторія була Internal → Google віддавав 403 org_internal
ще до екрана згоди; лікується Audience → Make external (не кодом і не в Supabase).
Apple залишається вимкненим.

Login UI (2026-10-21, запит власника): соціальні кнопки перенесено під «Увійти»,
формат — компактні іконки 52×52 у центрованому ряду з розділювачем «або увійдіть через».
Доступні назви `Продовжити з Google/Apple` збережено в aria-label, тому e2e не зламались:
tests/e2e/oauth-ui.spec.js 5 passed (390/1440 × light/dark). Apple-іконка з'явиться
автоматично, щойно провайдер буде увімкнений; окремої заглушки не додавали.

Навбар (2026-10-21): прибрано напис «Ви увійшли» (стан показує сама кнопка «Вийти»)
та `<select>` теми. Замість нього іконковий перемикач sun/moon `[data-theme-control]`
з анімацією падіння через @keyframes на зміну `data-theme`; prefers-reduced-motion
вимикає анімацію. Зберігається явний preference у localStorage, auto лишається
початковим станом. Оновлено session.js (без data-auth-status) і 4 e2e spec, що
керували темою через selectOption. Перевірки: e2e 30 passed, theme unit 6 passed.
Доопрацювання: hover на перемикачі прибрано (base.css інакше підставляє свій фон);
анімація падіння виконується лише після реального кліку через прапорець
`data-theme-animated` на корені, тому перезавантаження її не програє. Кнопка входу
тепер `hidden` до відповіді /api/session, із `<noscript>` запасним посиланням —
замість миготіння «Логін → Вийти» коротко порожній слот. e2e 37 passed.

Залишилось для реальної реєстрації: додати `AUTH_EMAIL_ENABLED=true` у `.env.local`
та пройти signup із підтвердженням. Живий signup ще не виконувався.

S03-06 поставлено на паузу за новим пріоритетом. Його чотири локальні integration
тести лишаються поведінковим RED і НЕ комітяться (інакше CI червоний); файли
`server/tests/integration/auth/test_refresh_session.py` та `.workflow/evidence/S03-06.json`
лишаються лише в робочому дереві. Не запускай Alembic і не додавай grants для refresh
без окремого рішення.

Повернення до послідовного roadmap за запитом власника. S00–S02 завершені;
S03-01..05 done. Додаткові landing/UI/OAuth child cards не означають завершення S04/S05.
S03-04: справжній local Supabase confirmation email,6-digit OTP, JWT, product profile,
server session, replay/expiry rejection, rollback/retry, member-only role, resend quota.
31 auth integration +96 regression/16subtests GREEN; read-only review clean.
AUTH_EMAIL_ENABLED=false за замовчуванням, незалежний від social flags.
S03-05: password login, opaque cookie rotation, generic401, independent email flag,
origin guard, rate limits, no-store на всіх auth/session responses.
35 Auth integration +79 regression GREEN; read-only review clean.
S03-06 — refresh singleflight/lease та atomic token swap — на паузі до завершення
першого етапу реєстраційної БД/runtime-підключення.
Поточний commit/push/CI перевіряються після комміту; попередній5096510 pushed,CI39427618056 green.

AUTH_DATABASE_URL — PostgreSQL connection string окремого restricted LOGIN, не API key.
Локальні таблиці керуються тестовою Alembic схемою; у хмарі для першого етапу
registration tables створені прямим одноразовим SQL bootstrap без migration ledger.
Runtime LOGIN/URL поки не налаштовані.

Supabase підтверджено: https://dwckvtuhgelhsbjyhpks.supabase.co.
Apple Developer account немає. G_AUTH_PROVIDERS env_blocked: runtime DB login,
Google config і live roundtrip ще не виконані; Apple вимкнений.
Окремий environment gate: підключення Supabase для перевірки нової БД та Google Client ID/Secret
у dashboard провайдера. Інструкція docs/oauth-project-setup.md.

## Попередній migration підхід (не використовувати для першого етапу)

Cloud migrations, `tools.migrate_cloud.py`, operator-only FK і відповідні докази
є історичними. Власник попросив не застосовувати міграції, а створити поточні
registration objects прямим SQL. Не повторно запускай Alembic bootstrap на цій хмарі.
Наступний технічний крок після DB bootstrap: безпечно задати пароль окремому
`studio_auth_runtime` LOGIN, внести URL локально без передачі секрету в чат,
перевірити підключення й виконати реальний signup/confirmation smoke test.

## Історія до спрощення (не чинна інструкція запуску)

Підготовка хмарної БД (2026-10-20, власник підтвердив використання цього project ref,
архівування старої `studio` зі збереженням об'єктів і запуск міграцій 0001–0006).
Read-only inventory до змін: 18 старих таблиць `studio`, усі 0 rows, 21 внутрішній FK
і один FK `studio.users -> auth.users`; чотири записи у керованому `supabase_migrations`.
Backup до DDL створено через PostgreSQL 17 session pooler і перевірено `pg_restore --list`:
`.local-tools/backups/studio-legacy-20261020.dump` (custom format, 143008 bytes,
mode 0600, git-ignored), SHA-256 `4963a511278c601f3f16e7c4400606cd107386e923de8a9d8a136e6ea8f281dc`.
Власник підтвердив зупинку старого runtime. `studio` перейменовано на
`studio_legacy_20261020`; усі 18 таблиць/об'єктів збережені. Створено `migration_owner`
(LOGIN, NO SUPERUSER/CREATEDB/CREATEROLE/BYPASSRLS, NOINHERIT) та NOLOGIN ролі
`studio_web`, `studio_auth_runtime`, `studio_worker` з least-privilege attributes.
Пароль `migration_owner` встановлено через `psql \\password`; dedicated login ще не
підтверджено окремим успішним підключенням.

SSL enforcement увімкнено (Supabase перезапустив БД; старий runtime підтверджено зупиненим).
Temporary Access preview увімкнено; правил доступу не створено. UI дозволяє лише
`migration_owner`, `postgres` і `supabase_read_only_user`; `supabase_auth_admin` не можна
видати тимчасово через цей механізм, тому додатковий доступ не надавався.

Блокер міграції: у `migration_owner` немає `USAGE` на managed `auth` і
`REFERENCES` на `auth.users(id)`. `postgres` має privilege без grant option і не може
`SET ROLE` у `supabase_admin` або `supabase_auth_admin`; `supabase_privileged_role` теж
не має потрібних прав. Пряме виконання поточної Alembic 0002 під `migration_owner`
залишається заблокованим. Не прибирати FK, не запускати всі міграції під `postgres`,
не `stamp`-ити й не змінювати managed Auth.

2026-10-21: знайдено і перевірено self-service шлях БЕЗ Support.
Supabase офіційно дозволяє FK до managed таблиць:
https://supabase.com/changelog/34270-restricting-access-on-auth-storage-and-realtime-schemas-on-april-21-2025
Rollback-only probe `.workflow/evidence/cloud_auth_fk_operator_probe.sql` виконано
через MCP SQL саме у поточній хмарній БД. `migration_owner` створив probe schema/table;
спроба додати FK під ним дала очікуваний insufficient_privilege. `postgres` додав FK;
потім INSERT неіснуючого Auth ID під `migration_owner` дав foreign_key_violation.
Власник таблиці не змінився, Auth privileges у `migration_owner` не з'явились.
Для оператора тимчасово дозволено INHERIT/SET membership у `migration_owner`
(НЕ зворотний напрямок і НЕ managed admin). Уся транзакція завершилась ROLLBACK.
Фінальний SELECT: probe_schema_absent, operator_set_restored, operator_inherit_restored,
migration_auth_usage_absent, migration_auth_references_absent = true.
Перша спроба probe впала на діагностиці has_column_privilege під migration_owner:
name resolution `auth.users` теж потребує USAGE. Перевірку тих самих відсутніх прав
перенесено в контекст postgres; ownership та FK rejection перевірені під migration_owner.
Це доказ механізму, НЕ застосування Alembic 0001–0006 і НЕ перевірка runtime.
Власник погодив цей виняток 2026-10-21 ("так"): лише DDL цього FK виконує
postgres у транзакції; решта DDL та ownership залишаються migration_owner.
Реалізовано explicit `Config.attributes["operator_auth_fk"] = True` для supplied
connection. `operator_auth_migration` перевіряє non-superuser postgres session,
тимчасово дозволяє membership INHERIT/SET, переходить у migration_owner і
відновлює попередній grant-row. Savepoints забезпечують rollback ролей/DDL
після SQL-помилки. Звичайний CLI не приймає postgres URL.
`tools/migrate_cloud.py` фіксує project/pooler і revision0006, запитує пароль
через getpass, використовує verify-full/явний Supabase CA; спочатку rollback rehearsal,
за `--apply` окрема перевірена транзакція з COMMIT. Runtime secrets не читає.
Тести: initial operator RED 2 failed/1 passed через відсутній режим;
потім baseline17 GREEN (upgrade/repeat, FK rejection, rollback/retry, opt-in,
4 membership variants і concurrent operator subprocesses). DB regression78
GREEN разом з URL/TLS unit7; після додавання explicit CA option unit8 GREEN. TLS test мав RED
require != verify-full перед виправленням. Ruff усіх6 touched Python files GREEN.
Read-only reviewer виявив TLS verification issue; виправлено verify-full.
Повторний review: блокувальних знахідок немає. Mypy4 source files GREEN з MYPYPATH=server.
Live password-free TLS probe показав: system CA недостатньо, issuer Supabase Root2021.
Офіційний CA завантажено через HTTPS-link з Dashboard у
`.local-tools/supabase/prod-ca-2021.crt` (публічний, git-ignored), fingerprint SHA256
807025AD50D4ED219D2C9C7D299C004F824EB00CF7F65AFEF607D07B72E6CAFA.
Повторний psycopg probe з verify-full і цим CA GREEN: TLS пройшов, сервер вимагає пароль.
Команда cloud apply: `uv run --locked python -m tools.migrate_cloud --ssl-root-cert
.local-tools/supabase/prod-ca-2021.crt --apply`. Пароль вводить власник у терміналі,
не через chat/tool input. Застосування не оголошувати успішним до COMMIT та перевірки.
Нове entrypoint RED: missing module; GREEN: повний локальний upgrade verifier.
Виправлення test harness: SQLAlchemy IntegrityError/DataError SQLSTATE23503/22012,
FK INSERT під table owner після restoration та rollback успішного retry для
ізоляції тестів; очікування FK/привілеїв не послаблені.
Cloud application ще НЕ виконано, очікує захищеного operator login; dedicated
migration_owner login/runtime LOGIN/AUTH_DATABASE_URL досі не перевірені/не створені.
Постійних cloud змін цей probe не залишив; додаткові grants через Support не є
єдиним шляхом. Temporary Access для цього механізму не потрібний, правил досі немає.

Supavisor username `[role].[project-ref]` підтримано локально у
`server/studio/migration_connection.py` та `server/alembic/env.py`; 6 unit tests і Ruff GREEN.
Dedicated `migration_owner` login не перевірено. `.env.local`: `SUPABASE_PUBLISHABLE_KEY`
заданий, `AUTH_DATABASE_URL` порожній; runtime LOGIN не створено. Файл ignored, mode 0600;
`TOKEN_ENCRYPTION_KEY` не друкувати й не перегенеровувати. Раніше його значення випадково
потрапило у вивід делегованого інструмента; ротацію не виконували, перед production
потрібно визначити залежні ciphertext і спланувати безпечну ротацію. Нові `studio`,
`studio_private`, Alembic version table/product tables у хмарі відсутні; міграції не застосовано.
Локальний origin127.0.0.1:8000 — припущення для першої перевірки.
Parents S03/S04 не завершені; core next S03-06. Session refresh/profile completion і підключення login UI ще не готові. Preview навмисно не підключає credentials.

Гілка task/execution-v4; origin ivan-zamurenko/handbalancers-studio.
Preview PID23006 port8000. User docs deletions, .vscode, Copilot files не чіпати.
Запуск preview: uv run --locked python tools/serve_preview.py.
Тести: PATH .local-tools/uv-env/bin і .local-tools/node/bin; UV_CACHE_DIR=.local-tools/uv-cache.
DB: DOCKER_HOST=unix://$HOME/.colima/studio-s01/docker.sock; unset DOCKER_CONTEXT.
uv run --locked python -m tools.check_migrations. Не --fresh на існуючій БД.
