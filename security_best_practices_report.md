# Безпека поточного застосунку — 2026-11-08

## Результат і межі

Власник підтвердив: сайт працює лише локально з хмарною Supabase, реальних
користувачів немає. Локальні виправлення перевірені; публічний запуск ще не готовий.
Це огляд коду, негативні тести та обмежені read-only перевірки хмари, не зовнішній
pentest і не гарантія неможливості злому. Поточний процес сервера не перезапускали;
новий код застосовується після його перезапуску.

База цього проходу: `a38ca1c1ef6d1fe66e0d799e8b9c97010e560a7b`.
Попередні виправлення та тести: [перший аудит](docs/security-review-2026-11-07.md).
Обсяг: наявні публічні сторінки та JS, email/password і Google через Supabase,
JWT/JWKS, cookies/CSRF/Origin, OAuth PKCE, refresh/logout, доступ до БД,
конфігурація сервера й залежності. Apple вимкнено за рішенням власника.
Майбутні платежі, відео, програми й адмінські операції не сертифіковані цим аудитом.

Застосовано офіційний OpenAI `security-best-practices` (Python/FastAPI та vanilla JS),
локальні `supabase` і `supabase-postgres-best-practices`. Код SQL/schema не змінювався.

## Знахідки за пріоритетом

### SEC-01 — High: історично розкритий ключ шифрування; відкрито

- Доказ: історичний `.workflow/CURRENT.md` фіксує потрапляння
  `TOKEN_ENCRYPTION_KEY` у tool-output; підтвердженої ротації немає.
- Вплив: особа, яка отримає також зашифровані записи сесій/спроб OAuth,
  зможе розшифрувати їх старим ключем. Сам ключ не дає доступу до БД.
- Це не доказ злому чи витоку даних користувачів. Немає реальних користувачів.
  Попередній вузький Git-скан не знайшов секрет у Git, але не скасовує інцидент.
- Read-only preflight: 3 local-session records, 0 чинних за local expiry,
  2 без revoked_at; 4 OAuth attempts, 0 чинних. Це агрегати на час перевірки,
  не гарантія відсутності upstream refresh sessions. SSL активний; поточна DB-роль
  без superuser/BYPASSRLS/CREATEROLE. `.env.local` має права 0600.
- Ключ, cloud records і працюючий сервер не змінювали. План завершення нижче.

### SEC-02 — Medium: синхронна БД блокувала сервер; виправлено

- Місце: `server/studio/auth/oauth.py:182`, `refresh.py:58`, `logout.py:25`,
  quota paths у `sessions.py` та `verification.py`.
- Сценарій: запит auth чекає БД, а `/health/live` у тому самому ASGI-процесі
  також зависає. Це посилює наслідки повільної БД/навантаження, не обходить права.
- Доказ: реальний PostgreSQL `pg_sleep(0.4)` у транзакції; health після 25 ms
  мав завершитися до 250 ms. До fix ці тести падали.
- Fix: `server/studio/auth/db_work.py:9` виконує повну коротку транзакцію в
  обмеженому пулі потоків; Session не передається між потоками/через await.
  Мережа до Supabase лишається поза транзакцією.
- Під час review відтворено регресію нового offload: скасування запиту могло
  звільнити refresh lease до завершення DB worker. Shield/drain тепер чекає
  завершення транзакції перед cleanup; окремий DB-тест це перевіряє.
  Якщо скасування сталося під час claim, lease може лишитися до TTL 30 секунд.

### SEC-03 — Medium: provider I/O без загального deadline/ліміту; виправлено

- Місце: `server/studio/auth/supabase_adapter.py:58`, `jwt.py:66`,
  новий `provider_http.py:6`.
- Сценарій: зовнішній сервер повільно надсилає chunks або надто велике тіло;
  inactivity timeout сам по собі не обмежує всю операцію. Потрібен збій/аномальна
  відповідь довіреного upstream; довільний користувацький URL тут не приймається.
- Fix: загальний timeout, streaming-ліміт 64 KiB на успішні й помилкові тіла,
  перевірка фактичних bytes навіть без/з неправдивим Content-Length,
  `Accept-Encoding: identity` і відхилення інших encoding до читання.
- Неправильний/надмірно вкладений JSON у 2xx тепер означає тимчасову недоступність,
  а не відхилення credentials, яке могло відкликати сесію. HTTP 400/401 зберігають
  чинний контракт. Тести перевіряють закриття stream, deadline та cancellation.

### SEC-04 — Medium: збій JWKS помилково завершував сесію; виправлено

- Місце: `server/studio/auth/jwt.py:81`, `refresh.py:77`,
  `verification_routes.py` (переклад помилок).
- Сценарій: local session і access JWT ще чинні, але JWKS endpoint недоступний;
  сервер відповідав 401. Після ротації signing key другий запит під час cooldown
  також міг перейти з тимчасової помилки в 401.
- Fix: `IdentityVerificationUnavailable` → 503/Retry-After без очищення cookie
  чи відкликання сесії; cooldown пам'ятає невдале оновлення. Перевірені кешовані
  ключі працюють у межах TTL. Відомо неправильний issuer/signature лишається 401.
  Доступ без успішної перевірки identity не надається.
- Доказ: реальна DB-сесія, два послідовні 503, лише один fetch; негативний issuer
  test та окремий warm-cache/key-rotation test.

### SEC-05 — Low: deployment Host та зайва API-схема; посилено

- Місце: `server/studio/main.py:25`.
- Production/staging приймають лише hostname з `PUBLIC_ORIGIN`, без автоматичного
  www redirect. Підроблений `X-Forwarded-Host` не обходить перевірку Host.
- `/openapi.json` доступний лише local/test; Swagger/ReDoc вже вимкнені.
  Публічна схема сама по собі не доводить вразливість; це зменшення зайвої поверхні.
- Невірний Host отримує стандартний plaintext 400 від TrustedHostMiddleware
  з security headers, до API JSON-handler. Edge health-check має передавати
  дозволений Host. Захист не замінює trusted-proxy configuration.

## Перевірки й підтримка

- 158 unit/contracts/auth-security, 75 auth integration із реальною локальною БД,
  45 браузерних тестів; Ruff/format/Mypy пройшли.
- 14 CI/tooling tests + 6 subtests пройшли. CI тепер перевіряє lockfile export
  через pinned `pip-audit==2.10.1 --strict` та `npm audit --audit-level=low`.
  Обидві реальні команди дали 0 відомих вразливостей на час перевірки.
  Помилка advisory-сервісу також зупинить цей крок; це свідомий fail-closed вибір.
- 59 database/20 RLS і 34 JS пройшли в попередньому аудиті та його CI;
  окремо в цьому проході їх не повторювали. Схема, grants/RLS і JS не змінювалися.
- Незалежний read-only reviewer перевірив core diff і CI. Обидва знайдені ним
  крайові випадки (cancellation і warm-cache outage) виправлені через RED/GREEN.
- Наявні перевірки cookie/CSRF, PKCE/replay, прав із БД, міжкористувацької ізоляції,
  logout/refresh races залишаються зеленими. Огляд не виявив нового підтвердженого
  обходу авторизації; це обмежений висновок, а не доказ відсутності всіх атак.
- Докази: `.workflow/evidence/security-best-practices-2026-11-08.json`.

## Конкретний наступний крок: ротація та хмарна готовність

1. Перед змінами повторити read-only counts: вони могли змінитися. Визначити всі
   runtime instances, що завантажили старий ключ, і припинити нові auth-запити.
2. Через підтримуваний Supabase Auth механізм відкликати залежні upstream сесії
   тестових акаунтів; підтвердити результат. Local expiry або local revoke не є
   доказом upstream revoke. Якщо старий access token уже непридатний для logout,
   потрібен операторський механізм, не припущення про успішний sign-out.
3. У транзакції відкликати залежні local sessions і завершити OAuth attempts;
   не видаляти акаунти чи історію. SQL підготувати й перевірити до виконання.
4. Створити новий випадковий ключ без друку, атомарно замінити секрет з правами
   0600/у secret store й перезапустити всі instances. Не повертати старий ключ.
   Його старі копії/ciphertext залишаються частиною оцінки інциденту.
5. Хмара за останнім підтвердженням на Alembic0006; runtime head0007 потребує
   додаткових UPDATE grants для refresh. Застосувати й перевірити0007 підтримуваним
   migration-процесом. Наявний `tools.migrate_cloud` навмисно обмежений0006:
   повтор його старої команди не закриває цей крок.
6. Перевірити: старі cookies відхилені, новий Google/email login, refresh і logout
   працюють; секрети не з'являються в логах. Лише тоді позначити ротацію завершеною.

До публікації окремо перевірити Supabase dashboard Security Advisor/redirect URLs,
MFA адміністратора, provider abuse limits/CAPTCHA, exposed schemas, HTTPS,
довірені proxy IP, edge time/body/concurrency limits і резервні копії.
Зовнішній pentest і ці deployment-параметри тут не перевірені. Cloud mutations,
deploy і ротацію не виконано. Roadmap не пересунуто: наступна картка S03-08.

## Джерела

- [OpenAI security-best-practices skill](https://github.com/openai/skills/blob/main/skills/.curated/security-best-practices/SKILL.md)
- [HTTPX timeout semantics](https://www.python-httpx.org/advanced/timeouts/)
- [Supabase session lifecycle](https://supabase.com/docs/guides/auth/sessions)
- [Supabase production checklist](https://supabase.com/docs/guides/security/production-checklist)
