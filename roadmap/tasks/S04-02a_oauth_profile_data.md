# S04-02a — Автоматичний імпорт OAuth профілю

Явний запит власника: Google/Apple та автоматичне збереження даних у БД.
Залежність: S04-01a. Parent S04-02 лишається todo.

Після перевірки JWT і UUID імпортувати optional display_name, first_name, last_name.
Повне ім’я не розділяти навмання. Metadata не визначає role/identity/access.
Повторний вхід заповнює лише NULL, зберігає ручні правки; без нових даних revision не змінюється.
Перевірити malformed metadata, concurrency, role grants і mismatched identity на реальній БД.
Міграція 0006, ORM parity проти актуального head. Provider HTTP у тестах синтетичний.

Підготувати інструкцію для підтвердженого Supabase project. Секрети лише локально.
Live gate окремо: провайдери, remote migrations і реальний roundtrip ще env_blocked.

Commit: `feat(auth): [S04-02a] import OAuth profile data`.
