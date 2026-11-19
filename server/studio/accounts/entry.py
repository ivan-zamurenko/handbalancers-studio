"""Resolve member entry from a verified session and stored questionnaire, never browser state."""

from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy.exc import SQLAlchemyError

from studio.accounts.onboarding import setup_required
from studio.auth.db_work import run_db
from studio.auth.jwt import InvalidIdentity
from studio.auth.refresh import RefreshUnavailable
from studio.auth.token_store import StoreError
from studio.db import UnsafeWebRole
from studio.shared.context import Actor


async def completion_required(request: Request, profile: dict[str, object]) -> bool:
    transaction = getattr(request.app.state, "web_transaction", None)
    if transaction is None:
        raise HTTPException(503)
    try:
        return await run_db(setup_required, transaction, Actor(UUID(str(profile["id"]))))
    except (SQLAlchemyError, UnsafeWebRole):
        raise HTTPException(503) from None


async def entry_destination(request: Request) -> str:
    from studio.auth.oauth_routes import service_for, session_name

    cookie = request.cookies.get(session_name(request))
    if not cookie:
        return "/login"
    try:
        profile = await service_for(request).session_profile(cookie)
    except (StoreError, InvalidIdentity):
        return "/login"
    except RefreshUnavailable:
        raise HTTPException(503) from None
    return "/profile" if await completion_required(request, profile) else "/dashboard"
