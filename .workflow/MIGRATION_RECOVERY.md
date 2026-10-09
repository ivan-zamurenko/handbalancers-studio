# Міграції: відмова, forward repair та відновлення

0001–0004 навмисно відхиляють downgrade. Автоматичний DROP product/managed
схем або reset наявного стенда не є способом виправлення помилки міграції.

## Невдалий upgrade

Alembic runner виконує upgrade в одній транзакції з advisory lock.
За помилки перевірити поточну revision під операторською роллю, локалізувати
причину й відтворити на новій ізольованій test БД. Не вважати нову revision
застосованою лише через наявність файлу. CI --fresh відмовляє при будь-якій
наявній studio/studio_private та ніколи не очищує їх.

## Forward repair

Для вже опублікованої/застосованої міграції додати наступну revision з
down_revision на єдину поточну head. Не переписувати її історію.
Спочатку написати перевірку зіпсованого стану й очікуваного виправлення;
перевірити upgrade з чистої БД та з попереднього head, constraints/grants/RLS,
повторний запуск і rollback. Запуск gate з кореня:

    uv run --locked python -m tools.check_migrations

На новому одноразовому CI stack:

    uv run --locked python -m tools.check_migrations --fresh

## Restore, якщо forward repair недостатній

Hosted/production restore потребує окремого дозволу власника, перевіреного
backup/PITR і конкретного target. Спочатку відновити копію в ізольованому
середовищі, звірити revision, managed Auth, FK, кількості/інваріанти даних,
grants/RLS та відсутність доступу runtime до чужих/private rows.
Лише після цієї перевірки погоджувати переключення чи заміну цільового стенда.
Реальний hosted restore/PITR у цьому проєкті ще не перевірений.

CI може видалити тільки власний ephemeral test stack через scoped stop
--no-backup. Цей cleanup не переноситься на локальну dev/test БД із даними.
