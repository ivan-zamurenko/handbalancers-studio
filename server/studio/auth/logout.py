"""Commit local revocation before bounded, best-effort upstream sign-out."""

import asyncio
from collections.abc import Callable
from contextlib import AbstractContextManager

from sqlalchemy.orm import Session

from studio.auth.gateway import AuthFailure, AuthGateway
from studio.auth.token_store import StoreError, TokenStore

UPSTREAM_TIMEOUT_SECONDS = 5.0


async def logout_session(
    cookie: str,
    *,
    transaction: Callable[[], AbstractContextManager[Session]],
    store: TokenStore,
    gateway: AuthGateway,
) -> bool | None:
    """Return upstream confirmed/unconfirmed/not-attempted; never undo local revoke."""
    with transaction() as session:
        try:
            tokens = store.read_session(session, cookie)
        except StoreError:
            tokens = None
        # Expiry or unreadable ciphertext must not prevent local revocation.
        store.revoke_session(session, cookie)
    if tokens is None:
        return None
    try:
        async with asyncio.timeout(UPSTREAM_TIMEOUT_SECONDS):
            await gateway.logout(tokens.access_token.get_secret_value())
    except (AuthFailure, TimeoutError):
        return False
    return True
