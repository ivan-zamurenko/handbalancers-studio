# DEFECT-auth-clock-skew — мінімальна різниця часу видачі JWT

Виявлено під час регресії S03-09, 2026-11-08. Це окрема поправка JWT,
не зміна правил CSRF/rate limit. Дозволений обсяг: auth/jwt.py,
security/auth/test_jwt_clock_skew.py, ця картка й evidence/checkpoint.

Проблема: реальна локальна Supabase видає підписаний токен з iat лише на10ms
попереду host. PyJWT відхиляє його як ImmatureSignatureError; login повертає401,
verify-email422. Safe diagnostic зафіксував iat_minus_host_seconds=0.01.

Рішення: лише для iat допуск максимум1s; тип залишається integer. Signature,
algorithm allowlist, issuer, audience, exp і nbf перевіряються як раніше.
Загальний JWT leeway не додається: він продовжив би строк дії exp.

Acceptance: реальний ES256 token при+10ms проходить; >1s відхиляється;
expired token навіть із майбутнім iat відхиляється; nbf у майбутньому
відхиляється; malformediat відхиляється. Existing JWT suite та real-local
Auth regression мають пройти без retries у runtime, skip або weakening.

RED: новий deterministic test —1failed/7passed. GREEN та review записані
у .workflow/evidence/DEFECT-auth-clock-skew.json. Окремий commit:
fix(auth): tolerate minimal JWT issuance clock skew
