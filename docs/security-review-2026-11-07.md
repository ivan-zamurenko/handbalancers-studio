# Перевірка безпеки — 2026-11-07

Локальну перевірку завершено 2026-11-08.

Перевірено реалізований сайт до S03-07 на базі `24102fd`:
FastAPI, браузерні сторінки, Google/email auth, JWT, cookies, CSRF, OAuth PKCE,
refresh/logout, SQL grants/RLS, конфігурацію та зафіксовані залежності.
Це локальний огляд коду й негативні тести, не зовнішній pentest production.
Абсолютної гарантії від злому така перевірка не дає.

## Знахідки та виправлення

| Знахідка | Доказ / вплив | Результат |
|---|---|---|
| Вразливий trust store `certifi` | Встановлено 2026.7.22; GHSA-6q48-6c7w-9gw2. Компрометований проміжний CA створює ризик перехоплення TLS для нападника на мережевому шляху. Advisory має critical severity; це не доказ перехоплення нашого трафіку. | Lockfile та середовище оновлено до 2026.10.19. |
| Вразливий `opentelemetry-api` | Встановлено 1.45.0; GHSA-xcq7-p3pf-p88h / CVE-2026-114603, дорогий розбір `tracestate`. Досяжність саме цього шляху через поточний HTTP runtime не доведена. | Оновлено до 1.45.1. |
| Розростання таблиці лімітів після 429 | Вичерпаний IP-бюджет не зупиняв INSERT нових email-buckets. Реальні DB-тести для login/verify/resend відтворили додаткові рядки. | IP-бюджет комітиться; заборонений клієнт більше не створює email-buckets. |
| Небезпечна deployment-конфігурація БД | Production/staging приймали відсутній `sslmode`, `disable`, `prefer`, `require`, `verify-ca`. Ці режими не дають потрібної перевірки hostname. | При активному auth потрібен `sslmode=verify-full`; інакше запуск відхиляється. Поточна локальна конфігурація cloud-підключення вже мала verify-full та CA. |
| Необмежений розмір JSON до перевірки полів | Межі Pydantic застосовувалися після завантаження/розбору тіла. Тести показали прийняття понад 64 KiB, у тому числі без правдивого Content-Length. | Загальний streaming-ліміт 64 KiB до JSON parsing; 413 у безпечному JSON-форматі, без логування body. Майбутні uploads потребують окремого продуманого контракту. |

Додаткове посилення: CSP, `nosniff` і `no-referrer` тепер діють також на API,
помилки та static; inline CSS більше не дозволено. Staging/production додають
HSTS на рік без includeSubDomains/preload. Swagger/ReDoc HTML вимкнено, бо
їхні CDN/inline scripts несумісні з CSP; `/openapi.json` збережено.

Поточний статичний огляд не виявив підтвердженого обходу авторизації, IDOR,
SQL injection, OAuth replay або SSRF. Це висновок у межах прочитаних шляхів,
а не твердження про відсутність усіх можливих вразливостей. Ролі читаються з БД;
metadata не підвищує права; cookies HttpOnly/SameSite, HTTPS cookies Secure;
Origin/CSRF, одноразовий PKCE, fencing refresh і негайне local revoke покриті тестами.

## Перевірки

- RED: 21 HTTP/config test failed, 2 passed; 3 реальні DB-тести відтворили
  необмежене додавання email-buckets. Окремий тест вимкнення CDN docs — RED.
- GREEN: 128 unit/contracts/auth-security, 59 database, 20 RLS/security,
  67 auth integration, 45 Playwright, 34 JavaScript. Ruff/format/Mypy пройшли.
- Спочатку 4 UI fixture-тести не пройшли через inline script/style injection
  самого тесту. Fixture тепер завантажує реальні зовнішні assets; очікування
  focus, keyboard, pending і responsive не змінені. Повтор: 45/45.
- `pip-audit` після оновлення: 0 відомих вразливостей у 41 встановленому пакеті;
  npm audit: 0. Початковий Python-звіт містив 3 записи, але 2 унікальні advisory:
  запис certifi повторився. Це поточний зріз бази advisory, не постійна гарантія.
- 983 доступні Git blobs перевірено на точні збіги з 3 поточними локальними
  секретними значеннями та вузький набір credential/private-key patterns:
  збігів не знайдено. Значення не друкувалися. Це не універсальний secret scanner;
  інші невідомі формати й дані поза Git не були повністю перевірені.
- Незалежний read-only review: блокувальних зауважень до виправлень немає.

## Що лишається перед публічним запуском

1. **Контрольована ротація ключа шифрування.** За попереднім CURRENT значення
   `TOKEN_ENCRYPTION_KEY` потрапило у tool-output; ротацію не зафіксовано.
   Відсутність ключа в Git цього не виправляє. Самого ключа недостатньо для
   читання БД, але його слід вважати потенційно розкритим. Ключ не змінювали
   під час аудиту, щоб не пошкодити чинні ciphertext без узгодженого переходу.
   Практичний варіант для цього етапу: перевірити кількість залежних sessions/
   OAuth attempts, підготувати maintenance window всіх runtime instances,
   відкликати старі локальні сесії, замінити ключ через secret store та вимагати
   нового входу. Пов'язані CSRF/rate-limit HMAC теж зміняться. Не повертати старий
   ключ у роботу; перевірити старі cookies, новий login, refresh і logout.
   Конкретний операторський dry-run та вплив на користувачів потрібно підготувати
   перед окремим виконанням; масового logout/зміни cloud-секретів тут не було.
2. **Хмарна перевірка.** Хмара за останнім checkpoint на Alembic0006, код на0007.
   До deploy потрібні застосування0007, hosted login/refresh/logout smoke та
   перевірка Supabase Security Advisor, exposed schemas/RLS, точних redirect URLs,
   rate limits/CAPTCHA, SSL enforcement, доступу до адміністративних акаунтів/MFA.
   Ці dashboard-параметри не перевірялися заново в цьому аудиті.
3. **Захист deployment від перевантаження.** Перевірити TLS/HTTPS redirect,
   довірені proxy IP (не довіряти довільному X-Forwarded-For), body/header/time/
   concurrency limits та edge rate limiting. Реєстрація наразі покладається на
   provider rate limits; локальні ліміти не замінюють захист прямого Supabase Auth API.
   Запланувати очищення старих rate-limit/OAuth/session рядків: fix обмежує записи
   після IP-відмови, але не створює політику зберігання чи захист від ботнету.
4. **Подальший контроль.** Аудит не охоплює ще не створені оплату, відео,
   персональні програми та адмінку. Повторювати dependency/security перевірки
   перед релізами й при додаванні приватних endpoint; налаштувати моніторинг,
   резервні копії та перевірку відновлення під час підготовки deployment.

Cloud settings, дані та секрети не змінено; deploy не виконано.
Власні попередні видалення docs та сторонні файли залишені як були.

## Джерела

- [certifi advisory](https://github.com/advisories/GHSA-6q48-6c7w-9gw2)
- [OpenTelemetry advisory](https://github.com/advisories/GHSA-xcq7-p3pf-p88h)
- [PostgreSQL TLS verification](https://www.postgresql.org/docs/current/libpq-ssl.html)
- [Starlette request size limits](https://www.starlette.io/routing/)
- [Supabase production security](https://supabase.com/docs/guides/security/production-checklist)
