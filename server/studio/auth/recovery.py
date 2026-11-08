"""One-shot recovery: provider OTP/tokens never become a product session."""

import asyncio
from uuid import UUID

from sqlalchemy import func, text, update

from studio.auth.db_work import run_db
from studio.auth.gateway import AuthFailure, AuthFailureKind
from studio.auth.jwt import InvalidIdentity, VerifiedIdentity
from studio.auth.models import WebSession
from studio.auth.oauth import OAuthService
from studio.auth.verification import quota


async def request_recovery(service: OAuthService, email: str, *, client_key: str) -> None:
    await run_db(quota, service, "recovery-request", email, client_key)
    try:
        await service.gateway.recovery(email)
    except AuthFailure as error:
        if error.kind in {AuthFailureKind.TIMEOUT, AuthFailureKind.UNAVAILABLE}:
            raise
        # Account existence, eligibility and provider email cooldown stay neutral.


def retire_sessions(service: OAuthService, identity: VerifiedIdentity) -> None:
    with service.transaction() as session:
        # Existing narrow grant maps a verified Auth UUID, including inactive users.
        # A never-provisioned verified user gets a minimal member profile, no session.
        user_id = session.scalar(
            text("SELECT studio_private.provision_member(:id, NULL, NULL, 'uk', 'UTC')"),
            {"id": identity.user_id},
        )
        if not isinstance(user_id, UUID):
            raise InvalidIdentity()
        session.execute(
            update(WebSession)
            .where(WebSession.user_id == user_id, WebSession.revoked_at.is_(None))
            .values(revoked_at=func.clock_timestamp())
        )


async def confirm_recovery(
    service: OAuthService, email: str, token: str, password: str, *, client_key: str
) -> None:
    await run_db(quota, service, "recovery-confirm", email, client_key)
    identity = None
    access = None
    try:
        async with asyncio.timeout(20):
            payload = await service.gateway.verify_recovery(email, token)
            if not isinstance(payload, dict):
                raise InvalidIdentity()
            access = payload.get("access_token")
            if not isinstance(access, str):
                raise InvalidIdentity()
            verified = await service.validator.verify(access)
            user = payload.get("user")
            if not isinstance(user, dict) or user.get("id") != str(verified.user_id):
                raise InvalidIdentity()
            identity = verified
            # DB failure must prevent password update.
            await run_db(retire_sessions, service, identity)
            result = await service.gateway.update_password(access, password)
            if not isinstance(result, dict) or result.get("id") != str(identity.user_id):
                raise AuthFailure(AuthFailureKind.UNAVAILABLE)
            # Issuance checks upstream AFTER committing its row. Global revocation
            # before the final local sweep closes the delayed pre-reset payload race.
            await service.gateway.logout_all(access)
    except TimeoutError:
        raise AuthFailure(AuthFailureKind.TIMEOUT) from None
    finally:
        # Outside the operation deadline: bounded DB/provider cleanup still runs
        # after cancellation or an ambiguous provider response, without retrying PUT.
        if identity is not None and isinstance(access, str):
            try:
                await run_db(retire_sessions, service, identity)
            finally:
                try:
                    await service.gateway.logout(access)
                except AuthFailure:
                    # Required global logout above determines success; this is cleanup.
                    pass
