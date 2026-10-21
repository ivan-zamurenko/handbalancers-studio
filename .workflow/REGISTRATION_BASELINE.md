# Прийняття реєстраційної БД під керування Alembic

2026-10-21: власник попросив знову спробувати міграцію після прямого SQL bootstrap.
Це дозволяє підготувати й застосувати перевірене прийняття поточної схеми.
Дозволу видаляти таблиці/дані, відновлювати старий runtime або розширювати права
для S03-06 ця зміна не дає.

## Фактичний стан

Хмарні `studio` і `studio_private` вже містять registration objects із
`supabase/bootstrap-registration.sql`. Перевірка лише читанням підтвердила
відповідність еталону `0006`. Власник успішно застосував adoption 2026-10-21;
post-commit перевірка підтвердила захищений `studio.alembic_version`, RLS,
збережену product schema та обидва виправлені default ACL.
До adoption журнал був відсутній: звичайний upgrade з base спробував би
повторно створити наявні об'єкти.

## Що робить новий режим

`tools.migrate_cloud --adopt-bootstrap` працює однією транзакцією з migration
advisory lock, lock timeout 5 секунд і statement timeout 60 секунд. Він:

1. Перевіряє owner, таблиці/колонки/defaults, constraints/FK, індекси, RLS,
   policies, точні definitions функцій, grants та відсутність зайвих triggers/rules.
   Невідомий стан відхиляється до запису історії. Фізичний порядок колонок неважливий.
2. Відтворює два відсутні ефекти `0001`: забирає у PUBLIC default EXECUTE для
   майбутніх функцій і default USAGE для майбутніх типів, створених postgres.
   Як і в оригінальній `0001`, це глобальні defaults власника, не лише Studio.
3. Після звірки записує baseline `0006` через Alembic stamp. Це прийняття
   еквівалентної схеми, а не твердження, що історичні CREATE виконані повторно.
4. Закриває доступ клієнтських/runtime ролей до журналу й вмикає на ньому RLS.
5. Повторно перевіряє baseline, ownership/RLS, FK та незмінність managed schemas.

Бізнес-дані не переписуються; `auth`, архів `studio_legacy_20261020` і журнал
Supabase migrations не змінюються. Помилка відкочує всю транзакцію.

Еталон `tools/registration_baseline_0006.json` містить лише hashes системного
каталогу, без акаунтів чи токенів. Integration-тест звіряє його з реальним
виконанням історичних міграцій та bootstrap на ізольованій PostgreSQL.
Два hashes функцій відповідають відомим відмінностям форматування/коментаря.

## Запуск власником

Потрібен пароль **postgres поточного Supabase-проєкту**, а не пароль користувача
сайту чи runtime `studio_app`. Ввести його тільки у прихований prompt локального
термінала. Скрипт не зберігає пароль; `.env.local` не змінюється.

Із кореня проєкту можна спочатку перевірити з rollback:

```sh
.venv/bin/python -m tools.migrate_cloud --adopt-bootstrap \
  --ssl-root-cert .local-tools/supabase/prod-ca-2021.crt
```

Для застосування тих самих перевірених дій:

```sh
.venv/bin/python -m tools.migrate_cloud --adopt-bootstrap \
  --ssl-root-cert .local-tools/supabase/prod-ca-2021.crt --apply
```

Успіх: `Applied baseline adoption to Alembic 0006; ownership and RLS verified.`
До цього повідомлення cloud adoption не позначати завершеним.
При mismatch не обходити перевірку звичайним `stamp`; дослідити названу категорію.
Історичні `0001–0006` не переписувати, bootstrap не запускати повторно.

Якщо команда повертає `phase=connect; reason=authentication_rejected`, сервер
відхилив пароль postgres до початку SQL. Це не пароль Dashboard, API key або
пароль studio_app. Якщо пароль невідомий, скинути його через
[Database → Settings](https://supabase.com/dashboard/project/dwckvtuhgelhsbjyhpks/database/settings),
зберегти локально в менеджері паролів і ввести новий пароль у прихований prompt.
Лапки та URL-кодування не потрібні; `.env.local` для цього не змінюється.
Не повторювати невдалі спроби з тим самим відхиленим паролем.
Якщо після скидання виникає помилка pooler, зберегти її безпечну категорію;
не скидати пароль багаторазово й не послаблювати TLS.
При `phase=commit` результат невідомий: спочатку перевірити стан БД.

[Офіційна інструкція скидання пароля](https://supabase.com/docs/guides/troubleshooting/how-do-i-reset-my-supabase-database-password-oTs5sB).

Після adoption наступні зміни робити новими Alembic revisions із перевірками
на локальному стенді. Цей режим прив'язаний до `0006`, не є універсальним repair.

Семантика stamp: [офіційна документація Alembic](https://alembic.sqlalchemy.org/en/latest/api/commands.html#alembic.command.stamp).
