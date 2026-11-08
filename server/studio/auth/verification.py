"""Email verification orchestration; OTP storage and validation belong to Supabase."""

import hashlib
import hmac

from studio.auth.db_work import run_db
from studio.auth.gateway import AuthFailure, AuthFailureKind
from studio.auth.oauth import OAuthRateLimited, OAuthResult, OAuthService
from studio.auth.rate_limit import allow_start


def quota(service: OAuthService, action: str, email: str, client_key: str) -> None:
    # Independent account/IP budgets prevent email rotation and cross-worker races.
    def bucket(value: str) -> str:
        return hmac.new(service.secret, value.encode(), hashlib.sha256).hexdigest()

    with service.transaction() as session:
        client_allowed = allow_start(session, bucket(f"{action}:ip:{client_key}"))
        # Commit the IP budget, but do not insert attacker-chosen email buckets
        # after it is exhausted. Raising inside the transaction would roll it back.
        email_allowed = client_allowed and allow_start(
            session,
            bucket(f"{action}:email:{email.casefold()}"),
            limit=1 if action in {"resend", "recovery-request", "recovery-confirm"} else 10,
        )
    if not client_allowed or not email_allowed:
        raise OAuthRateLimited()


async def verify_email(
    service: OAuthService,
    email: str,
    token: str,
    *,
    client_key: str,
    old_cookie: str | None = None,
) -> OAuthResult:
    await run_db(quota, service, "verify", email, client_key)
    payload = await service.gateway.verify_email(email, token)
    return await service.accept_identity(payload, old_cookie=old_cookie)


async def resend(service: OAuthService, email: str, *, client_key: str) -> None:
    await run_db(quota, service, "resend", email, client_key)
    try:
        await service.gateway.resend_verification(email)
    except AuthFailure as error:
        if error.kind in {AuthFailureKind.TIMEOUT, AuthFailureKind.UNAVAILABLE}:
            raise
        # Existing, unknown, confirmed and provider-cooldown outcomes stay neutral.
