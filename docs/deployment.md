# Запуск у Docker та розгортання

Ці файли описують запуск Handbalancer’s Studio на одному Linux VPS: PostgreSQL 17 → міграції Alembic → FastAPI → nginx із HTTPS. Конфігурацію підготовлено в проєкті; сервер, DNS, сертифікати та зовнішні облікові записи автоматично не створювалися. Docker і nginx у середовищі розробки відсутні: контейнерний запуск, Linux-сумісність залежностей та наведені операційні процедури потребують перевірки на окремому тестовому сервері перед публікацією.

Для запуску без Docker див. [локальну інструкцію](local-development.md). Секрети вводять локально у приватний файл або сховище секретів, без чату, Git чи скриншотів.

## Чому дві конфігурації

| Властивість        | `compose.yaml`                      | `compose.production.yaml`                |
| ------------------ | ----------------------------------- | ---------------------------------------- |
| Адреса             | `http://127.0.0.1:8000`             | `https://STUDIO_HOST`                    |
| Опубліковані порти | API лише на `127.0.0.1:8000`        | nginx на 80 і 443                        |
| PostgreSQL         | Приватна мережа, без порту на хості | Приватна мережа, без порту на хості      |
| Локальний preview  | Вимкнений; demo запускають нативно  | Примусово вимкнений                      |
| HTTPS              | Немає                               | TLS 1.2/1.3, HTTP перенаправляє на HTTPS |

Production-файл запускають **самостійно** через `-f compose.production.yaml`. Не об’єднуйте обидва файли: злиття могло б успадкувати локальний порт API. Різні назви Compose-проєктів також відокремлюють томи з даними.

API працює від користувача без root, із файловою системою лише для читання. Запис дозволено в обмежений тимчасовий каталог. База має окремий адміністративний пароль; застосунок використовує роль `studio` без superuser, створення інших баз і ролей. Наразі ця роль також володіє схемою для міграцій. Подальший поділ прав runtime і міграцій — окреме посилення доступів, а не вже виконана властивість.

## Приватні налаштування

У корені проєкту виконайте для локального Docker:

```sh
python3 deploy/create_env.py --output .env.compose.local
docker compose --env-file .env.compose.local -f compose.yaml config --quiet
docker compose --env-file .env.compose.local -f compose.yaml up -d --build api
docker compose --env-file .env.compose.local -f compose.yaml exec -T api python /app/healthcheck.py
```

Генератор записує випадкові паролі та session secret у новий файл із правами `0600`; значення не друкуються, наявний файл не перезаписується. `.env.*` виключено з Git і Docker build context. Не запускайте `docker compose config` без `--quiet`: розгорнута конфігурація містить секрети. Доступ до Docker daemon і приватного env-файла фактично дає доступ до налаштувань застосунку.

У `server/.env.example` перелічено всі змінні. Compose формує власний `DATABASE_URL` для приватного hostname `db`. Генератор використовує URL-безпечний hex-пароль; при ручній зміні `APP_DATABASE_PASSWORD` дотримуйтеся цього формату. Рядок `DATABASE_URL` у створеному файлі призначений для контейнерної адресації, тому не підходить для прямого запуску Python на хості.

Обидва Compose-файли примусово передають `LOCAL_PREVIEW=false`. Демонстраційний вхід і оплата додатково вимагають справжнього loopback peer; контейнер отримує з’єднання через Docker bridge, навіть коли порт опублікований на `127.0.0.1`. Для demo використовуйте нативний `scripts/local.py` за локальною інструкцією. Docker призначений для перевірки звичайного застосунку й налаштованих провайдерів. Production завжди передає `APP_ENV=production`, `LOCAL_PREVIEW=false` і HTTPS-origin; backend також перевіряє ці умови та довжину `SESSION_SECRET`.

Ініціалізаційний SQL PostgreSQL виконується лише для **порожнього** тому. Зміна пароля в env-файлі не змінює пароль уже створеної ролі: ротація потребує окремого оновлення в PostgreSQL і погодженого перезапуску залежних сервісів. Не видаляйте том заради ротації.

## Перший production-запуск і сертифікат

Потрібні Linux VPS, Docker Engine із плагіном Compose v2, SSH-доступ адміністратора та керований DNS. Для поточної конфігурації використовується один hostname. Його A-запис має вести на VPS; AAAA додавайте лише за робочого IPv6. Відкрийте 80/443 на мережевому та локальному firewall; SSH обмежте адміністративним доступом. БД і API не публікуйте окремими портами.

У прикладах каталог сервера — `/opt/handbalancers-studio`, а `studio.example.com` треба замінити власним доменом. Назва має бути ASCII DNS hostname без протоколу, шляху чи порту; для міжнародного домену використовуйте його punycode-подання.

```sh
cd /opt/handbalancers-studio
python3 deploy/create_env.py --output .env.compose.production --host studio.example.com
```

Відкрийте приватний файл у локальному редакторі на сервері й заповніть `ACME_EMAIL` для контактів щодо сертифіката. За потреби внесіть OAuth і Stripe налаштування з наступного розділу. Не вмикайте трасування shell (`set -x`) під час роботи із секретами.

```sh
docker compose --env-file .env.compose.production -f compose.production.yaml config --quiet
docker compose --env-file .env.compose.production -f compose.production.yaml up -d --build api nginx
docker compose --env-file .env.compose.production -f compose.production.yaml exec -T api python /app/healthcheck.py
```

`db` має пройти healthcheck до міграції. Якщо `alembic upgrade head` завершується помилкою, залежний API не запускається. Ця послідовність визначається [умовами залежностей Compose](https://docs.docker.com/compose/how-tos/startup-order/).

Поки сертифіката немає, nginx надає HTTP лише для ACME challenge та технічного `/_proxy/live`; інші запити отримують `503`. Застосунок через HTTP недоступний, порт 443 ще не має TLS listener. Випуск першого сертифіката виконують **на VPS**, коли DNS уже поширився:

```sh
docker compose --env-file .env.compose.production -f compose.production.yaml run --rm --no-deps --entrypoint /bin/sh certbot -c '
  test -n "$ACME_EMAIL" || { echo "Set ACME_EMAIL in the private env file" >&2; exit 1; }
  exec certbot certonly --webroot -w /var/www/certbot \
    --cert-name "$STUDIO_HOST" -d "$STUDIO_HOST" \
    --email "$ACME_EMAIL" --agree-tos --non-interactive
'
docker compose --env-file .env.compose.production -f compose.production.yaml up -d --force-recreate nginx
curl --fail --silent --show-error https://studio.example.com/health/ready
```

Повторний запуск nginx обирає TLS-шаблон, якщо сертифікат і ключ існують. Пошкоджений сертифікат спричиняє помилку `nginx -t`; застосунок не відкривається через HTTP як запасний варіант. Перевірте у браузері довірений сертифікат, перенаправлення HTTP → HTTPS та `Secure`-cookie після реальної авторизації. Сам `/_proxy/live` доводить лише роботу nginx, а `/health/ready` також перевіряє БД і схему.

За контейнерного способу Certbot отримує файли сертифіката, але не налаштовує nginx автоматично. Тут challenge-каталог і сертифікати передаються спільними томами; nginx читає їх без права запису. [Документація Certbot для Docker](https://eff-certbot.readthedocs.io/en/stable/install.html#alternative-1-docker).

Мережа `edge` використовує `172.30.100.0/24`, nginx має адресу `172.30.100.10`. Uvicorn довіряє proxy headers лише від неї, а nginx перезаписує отримані від клієнта headers. Перевірте відсутність конфлікту з мережами VPS/VPN; за зміни підмережі одночасно змініть IP nginx та `--forwarded-allow-ips`. За зовнішнього CDN або іншого проксі потрібно окремо узгодити модель довіри — цей файл їх не передбачає.

## Google, Apple та Stripe

Власний Stripe-акаунт не створює налаштувань Google або Apple. Це окремі інтеграції. Наявність env-полів означає підготовлений код інтеграції; успішний вхід і оплату треба підтвердити з вашими обліковими записами.

| Сервіс | Що внести приватно                                                                                   | Точна адреса для production                                                |
| ------ | ---------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Google | OAuth client типу Web application: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`                        | Authorized redirect URI: `https://studio.example.com/auth/google/callback` |
| Apple  | Services ID для web: `APPLE_CLIENT_ID`; згенерований чинний client-secret JWT: `APPLE_CLIENT_SECRET` | Return URL: `https://studio.example.com/auth/apple/callback`               |
| Stripe | `STRIPE_SECRET_KEY`, endpoint signing secret `STRIPE_WEBHOOK_SECRET`; чотири `STRIPE_PRICE_*`        | Webhook endpoint: `https://studio.example.com/api/webhooks/stripe`         |

Замініть домен у **кожній** адресі власним `STUDIO_HOST`. Google повертає користувача через GET, Apple використовує HTTPS POST із `response_mode=form_post`; проксі має зберігати цей POST. Для Google також налаштуйте consent screen, аудиторію та дозволених тестових користувачів відповідно до режиму OAuth-проєкту. [Google: web server OAuth](https://developers.google.com/identity/protocols/oauth2/web-server).

Для Apple потрібне налаштування Sign in with Apple у вашому developer-акаунті: пов’язаний App ID, Services ID, дозволений домен/Return URL та ключ. Сам `.p8`-ключ не передається цьому застосунку: чинний JWT формується в довіреному середовищі й має бути замінений до завершення його строку. Не купуйте членство автоматично лише для перевірки макета; спочатку перевірте доступні можливості вашого акаунта. [Apple: web configuration](https://developer.apple.com/help/account/capabilities/configure-sign-in-with-apple-for-the-web/), [client secret](https://developer.apple.com/documentation/accountorganizationaldatasharing/creating-a-client-secret).

Stripe починають у sandbox/test mode. У ньому створіть чотири місячні recurring Prices для Essential, Plus, Pro, Pro+ з погодженими сумами й валютою. Усі ключі, Price IDs та webhook secret мають належати одному режиму й акаунту. Для webhook виберіть `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.paid`, `invoice.payment_failed`. Перевірте фактичні суми в Stripe перед переходом у live mode: текст на сайті не змінює ціну Stripe. Підписка активується за перевіреною сервером подією, а не лише за поверненням із Checkout. [Stripe: webhook signatures](https://docs.stripe.com/webhooks#verify-events), [тестування](https://docs.stripe.com/testing).

Після внесення провайдерів відтворіть API командою `up -d --force-recreate api` з тим самим production `--env-file` і `-f`. Зміни `STUDIO_HOST` потребують також нового сертифіката, callback URL і відтворення nginx. Для кінцевого приймання перевірте відмову OAuth, прострочений/повторний callback, збереження анонімної анкети після входу, тестову оплату, повторний webhook та скасування підписки.

## Автоматичне поновлення TLS

Спершу вручну перевірте ACME renewal на тестовому endpoint, а тоді робочий host-side скрипт:

```sh
docker compose --env-file .env.compose.production -f compose.production.yaml run --rm --no-deps certbot renew --dry-run --webroot -w /var/www/certbot
sh deploy/renew-certificates.sh /opt/handbalancers-studio/.env.compose.production
```

Скрипт запускає `renew`, а після успіху — `nginx -t` і reload. Reload потрібний, щоб процес nginx почав використовувати новий сертифікат; заміни файлів на диску недостатньо. Він безпечний і коли поновлення ще не потрібне. Docker socket до Certbot не монтується. [Поновлення Certbot](https://eff-certbot.readthedocs.io/en/stable/using.html#renewing-certificates).

На VPS із systemd адаптуйте шляхи в `deploy/systemd/studio-cert-renew.service`, якщо каталог інший. Потім установіть обидва файли й увімкніть timer:

```sh
sudo cp deploy/systemd/studio-cert-renew.service /etc/systemd/system/
sudo cp deploy/systemd/studio-cert-renew.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now studio-cert-renew.timer
sudo systemctl list-timers studio-cert-renew.timer
```

Timer запускає перевірку двічі на добу з випадковою затримкою. Його помилки та зовнішній строк сертифіката потрібно моніторити; наявність timer не гарантує поновлення при зламаному DNS чи закритому порту 80. Підключення сповіщень тут не налаштовано.

## Очищення прострочених сесій

Для видалення лише прострочених browser sessions і OAuth attempts є окрема команда. Заплануйте її щоденний запуск і контроль помилок на VPS; cron або timer для неї тут не встановлювався. Ручний запуск:

```sh
docker compose --env-file .env.compose.production -f compose.production.yaml run --rm --no-deps api python -m studio.cleanup
```

Команда не видаляє профілі, анкети, користувачів, підписки чи платежі. Вона не замінює погодження строків зберігання продуктових і клієнтських даних.

Нативний еквівалент із налаштованим приватним середовищем — `python -m studio.cleanup` з каталогу `server`.

## Резервні копії та перевірка відновлення

Named volume переживає заміну контейнера, але не є резервною копією. `docker compose down -v` видаляє томи; не використовуйте цю команду для зупинки, оновлення або виправлення пароля.

```sh
sh deploy/backup-database.sh /opt/handbalancers-studio/.env.compose.production /srv/handbalancers-backups studio
```

Останній аргумент явно задає назву БД: зазвичай `studio`, після перемикання — значення `APP_DATABASE_NAME`. Скрипт створює custom-format `pg_dump` з правами доступу лише власника; при помилці прибирає неповний файл. Копія містить таблиці, дані та Alembic revision, але не налаштування провайдерів, ключі TLS, Docker volumes metadata або ролі всього PostgreSQL-кластера. Тримайте env-файл і сертифікати в окремій захищеній резервній процедурі; для нового хоста certbot також може випустити новий сертифікат. `pg_dump` дає узгоджений знімок БД на час початку копіювання. [PostgreSQL: pg_dump](https://www.postgresql.org/docs/17/app-pgdump.html).

Зберігайте зашифровану копію поза VPS. Розклад, термін зберігання, ключ шифрування, перевірка вільного місця й сповіщення про збій треба призначити відповідальному оператору; автоматизації backup або off-site storage у цьому пакеті немає.

Спочатку відновіть **власну довірену** копію в окремий PostgreSQL 17 / тестовий Compose-проєкт. Команди нижче виконують у каталозі цього окремого проєкту з його приватним env-файлом; вони створюють нову `studio_restore_check`, не підміняють чинну `studio`:

```sh
docker compose --env-file .env.compose.production -f compose.production.yaml up -d db
docker compose --env-file .env.compose.production -f compose.production.yaml exec -T db createdb --username=postgres --owner=studio studio_restore_check
docker compose --env-file .env.compose.production -f compose.production.yaml exec -T db pg_restore --username=studio --dbname=studio_restore_check --no-owner --no-acl --exit-on-error --single-transaction < /srv/handbalancers-backups/SELECTED-BACKUP.dump
```

`SELECTED-BACKUP.dump` замініть конкретним файлом. Перевірте кількість записів і потрібні дані, Alembic revision та запуск копії застосунку з **тестовою** відновленою БД: у тестовому Compose env-файлі встановіть `APP_DATABASE_NAME=studio_restore_check` до відтворення API/міграцій. Для прямого Python-запуску змінюється `DATABASE_URL`. Нова назва не створює БД автоматично: це вже зробила команда `createdb`. Не підключайте цей застосунок до live Stripe/OAuth і не копіюйте клієнтські дані в незахищене середовище. Успішний `pg_restore` доводить читабельність архіву, але ще не доводить відновлення всього продукту. [PostgreSQL: pg_restore](https://www.postgresql.org/docs/17/app-pgrestore.html).

Відновлення production потребує окремого maintenance window: зупинити API, створити свіжу копію, відновити у нову БД, перевірити її, змінити підключення й запустити сумісну версію застосунку. За потреби узгодьте повторне доставлення Stripe events після простою. Цей runbook навмисно не містить автоматичного видалення робочої БД.

## Оновлення й спостереження

Перед релізом перевірте backup/restore, сумісність міграції зі старою версією та межу допустимого простою. Для поточної односерверної схеми використовуйте коротке погоджене maintenance window: backup → `stop api` → `build` → `run --rm migrate` → `up -d api nginx`, завжди з явними production `--env-file` і `-f`. Якщо міграція не пройшла, не запускайте API поверх невідомого стану схеми. Зворотне перемикання образу не відкочує зміни даних; безпечний відкат залежить від конкретної міграції й перевіреної копії.

Зовні контролюйте HTTPS `/health/ready`, строк сертифіката та доступність сайту; на VPS — місце на диску, пам’ять, стан контейнерів, timer і backup. `/health/live` перевіряє процес, `/health/ready` — його готовність працювати з БД. Compose healthcheck позначає стан, але сам по собі не перезапускає процес, який лишився живим і нездоровим. Наявний `restart: unless-stopped` реагує на завершення процесу.

Uvicorn access log вимкнений. Nginx access log не містить query, cookies, referer чи body; запитні error logs вимкнено, бо вони могли б містити OAuth code. Помилки старту nginx лишаються в stderr; для runtime збоїв доступні HTTP status і health, а метрики потребують підключення моніторингу. Контейнерні логи обмежені розміром. Логи все ще містять IP та URI, тому доступ і строк зберігання також мають бути обмежені.

Nginx обмежує `/api/session` та `/auth/` окремими лімітами 10 запитів за хвилину на IP із коротким burst до 5; перевищення дає `429`. Це стримує просте створення зайвих сесій і повторні спроби входу. Користувачі спільного Wi-Fi/NAT ділять ліміт; під реальним трафіком перевірте баланс доступності й захисту. Таке обмеження не замінює захист від розподіленого DDoS або очищення прострочених сесій у БД.

Образи задають версії Python 3.13, PostgreSQL 17.11, nginx 1.30.4 і Certbot 5.8.0; образи тут не завантажувалися. Наявність трьох точних service tags та платформ amd64/arm64 перевірено через публічний Docker Hub metadata API; результат збережено в `deploy/image-tags.checked.json`. Це не є перевіркою запуску. Runtime Python-залежності зафіксовані в `server/requirements.lock`, перевіреному локально на macOS arm64. Теги образів і build-залежність setuptools не є незмінними digest-locks; перед релізом потрібні Linux build, перевірка вразливостей та за потреби фіксація digest перевірених образів. Оновлюйте security patches контрольовано з повторною перевіркою, а не припускайте довічну безпеку за номером версії.

Локальні тести deployment (`python -m unittest discover -s deploy/tests -v` у Python-середовищі з PyYAML) перевіряють приватне створення env, відмову від перезапису, межі Compose, proxy headers, поведінку healthcheck та обробку збою backup через підставний Docker CLI. Вони не виконують справжній dump/restore і не доводять роботу nginx або ACME. За відсутності Docker CLI відповідна синтаксична перевірка Compose явно пропускається.
