"""Cross-worker refresh with short DB leases, fenced completion and bounded I/O."""

import asyncio
import json
import time
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from studio.accounts.provisioning import current_profile
from studio.auth.gateway import AuthFailure, AuthFailureKind, AuthGateway
from studio.auth.jwt import InvalidIdentity, JWTValidator, VerifiedIdentity
from studio.auth.token_store import TokenStore

WAIT_SECONDS = 6.0
EXCHANGE_SECONDS = 5.0


class RefreshUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__("Session refresh temporarily unavailable")


async def refresh_identity(
    cookie: str,
    *,
    transaction: Callable[[], AbstractContextManager[Session]],
    store: TokenStore,
    gateway: AuthGateway,
    validator: JWTValidator,
) -> VerifiedIdentity:
    try:
        return await _refresh_identity(
            cookie, transaction=transaction, store=store, gateway=gateway, validator=validator
        )
    except (SQLAlchemyError, TimeoutError):
        # Never serialize DB parameters or upstream response bodies.
        raise RefreshUnavailable() from None


async def _refresh_identity(
    cookie: str,
    *,
    transaction: Callable[[], AbstractContextManager[Session]],
    store: TokenStore,
    gateway: AuthGateway,
    validator: JWTValidator,
) -> VerifiedIdentity:
    deadline = time.monotonic() + WAIT_SECONDS
    while True:
        with transaction() as session:
            tokens = store.read_session(session, cookie)
            if tokens.access_expires_at > datetime.now(UTC):
                version = None
                fresh = True
            else:
                fresh = False
                version = store.claim_refresh(session, cookie)
                if version is not None:
                    # Re-read after winning the CAS, including current active identity.
                    tokens = store.read_session(session, cookie)
                    profile = current_profile(session, tokens.user_id)
        if fresh:
            return await validator.verify(tokens.access_token.get_secret_value())
        if version is not None:
            break
        if time.monotonic() >= deadline:
            raise RefreshUnavailable()
        await asyncio.sleep(0.05)

    try:
        try:
            # One attempt per request. No DB connection/transaction across these awaits.
            async with asyncio.timeout(EXCHANGE_SECONDS):
                payload = await gateway.refresh(tokens.refresh_token.get_secret_value())
                if not isinstance(payload, dict):
                    raise RefreshUnavailable()
                access, refresh = payload.get("access_token"), payload.get("refresh_token")
                if not isinstance(access, str) or not isinstance(refresh, str) or not refresh:
                    raise RefreshUnavailable()
                # Match the encrypted-envelope plaintext bound before storage.
                if len(json.dumps({"access": access, "refresh": refresh}).encode()) > 65536:
                    raise RefreshUnavailable()
                try:
                    identity = await validator.verify(access)
                except InvalidIdentity:
                    # The validator also uses this error for unavailable JWKS.
                    # Deny this request, but do not permanently revoke on ambiguity.
                    raise RefreshUnavailable() from None
                if (
                    identity.user_id != profile["auth_user_id"]
                    or identity.session_id != tokens.upstream_session_id
                    or identity.expires_at <= time.time()
                ):
                    raise InvalidIdentity()
        except AuthFailure as error:
            if error.kind in {
                AuthFailureKind.TIMEOUT,
                AuthFailureKind.UNAVAILABLE,
                AuthFailureKind.RATE_LIMIT,
            }:
                raise RefreshUnavailable() from None
            raise InvalidIdentity() from None
        with transaction() as session:
            saved = store.complete_refresh(
                session,
                cookie,
                version,
                access_token=access,
                refresh_token=refresh,
                access_expires_at=datetime.fromtimestamp(identity.expires_at, UTC),
            )
            if not saved:
                # Local logout/expiry is terminal; loss of lease is temporary.
                store.read_session(session, cookie)
                raise RefreshUnavailable()
        return identity
    except InvalidIdentity:
        with transaction() as session:
            store.release_refresh(session, cookie, version, revoke=True)
        raise
    finally:
        # Cancellation and transient failure leave the session retryable. If the DB
        # itself is down the committed lease expires; only this version may release it.
        with transaction() as session:
            store.release_refresh(session, cookie, version)
