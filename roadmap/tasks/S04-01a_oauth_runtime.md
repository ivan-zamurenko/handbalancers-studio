# S04-01a — Серверний OAuth PKCE

Явний запит власника: Google та Apple через OAuth. Незалежний вертикальний
зріз поверх S01-06/S03-02, без оголошення решти S03/S04 виконаними.
Scope: oauth service/routes/runtime, narrow provisioning, settings/main,
міграція 0005, DB/HTTP тести, CI включення auth suite, env example/setup docs.
Acceptance: різні verifier, trusted callbacks/return path, binding, expiry,
одноразове consume COMMIT перед exchange, справжній JWT, member provisioning,
opaque cookie після commit, поточний активний profile, session rotation,
CSRF logout з local revoke перед мережею, DB quota 10 starts/IP/minute.
Тільки upstream HTTP синтетичний; DB/crypto/locks справжні.
Session expiry = access JWT expiry. Refresh, profile completion і email/password
ще не готові. Gate G_AUTH_PROVIDERS env_blocked: власник підтвердив, що
Google/Apple ще не налаштовані. Код не доводить успішний live roundtrip.
Перевірка: uv run python -m tools.check_migrations.
Commit: feat(auth): [S04-01a] add server OAuth PKCE flow
