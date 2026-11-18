"""Thin HTTP for own profile/preferences; identity only from the session cookie."""

from typing import Annotated, Literal
from uuid import UUID
from zoneinfo import available_timezones

from fastapi import APIRouter, HTTPException, Request
from pydantic import AfterValidator, BaseModel, ConfigDict, Field
from starlette.responses import JSONResponse

from studio.accounts import onboarding, service
from studio.auth.csrf import require_csrf
from studio.auth.db_work import run_db
from studio.auth.jwt import InvalidIdentity
from studio.auth.oauth_routes import HEADERS, service_for, session_name
from studio.auth.refresh import RefreshUnavailable
from studio.auth.routes import same_origin
from studio.auth.schemas import Name
from studio.auth.token_store import StoreError
from studio.shared.context import Actor

router = APIRouter(prefix="/api/me")


def _timezone(value: str) -> str:
    if value not in available_timezones():
        raise ValueError("Unknown timezone")
    return value


class ProfilePatch(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    first_name: Name | None = None
    last_name: Name | None = None
    locale: Literal["uk", "en"] | None = None
    timezone: Annotated[str, AfterValidator(_timezone)] | None = None


class PreferencesPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    theme_preference: Literal["auto", "light", "dark"]
    expected_revision: int = Field(ge=0, le=2_147_483_647)


async def _actor(request: Request, *, mutating: bool) -> tuple[Actor, service.WebTransaction]:
    transaction = getattr(request.app.state, "web_transaction", None)
    if transaction is None:
        raise HTTPException(503)
    if mutating:
        same_origin(request)
    oauth = service_for(request)
    cookie = request.cookies.get(session_name(request))
    if not cookie:
        raise HTTPException(401)
    try:
        profile = await oauth.session_profile(cookie)
    except (StoreError, InvalidIdentity):
        raise HTTPException(401) from None
    except RefreshUnavailable:
        raise HTTPException(503, headers={"Retry-After": "5"}) from None
    if mutating:
        require_csrf(request, oauth.csrf_token(cookie))
    return Actor(UUID(str(profile["id"]))), transaction


@router.get("/profile")
async def read_profile(request: Request) -> JSONResponse:
    actor, transaction = await _actor(request, mutating=False)
    return JSONResponse(await run_db(service.get_profile, transaction, actor), headers=HEADERS)


@router.patch("/profile")
async def patch_profile(request: Request, data: ProfilePatch) -> JSONResponse:
    actor, transaction = await _actor(request, mutating=True)
    changes = data.model_dump(exclude_none=True)
    profile = await run_db(service.update_profile, transaction, actor, changes)
    return JSONResponse(profile, headers=HEADERS)


@router.get("/preferences")
async def read_preferences(request: Request) -> JSONResponse:
    actor, transaction = await _actor(request, mutating=False)
    current = await run_db(service.get_preferences, transaction, actor)
    return JSONResponse(current, headers=HEADERS)


@router.patch("/preferences")
async def patch_preferences(request: Request, data: PreferencesPatch) -> JSONResponse:
    actor, transaction = await _actor(request, mutating=True)
    try:
        current = await run_db(
            service.update_preferences,
            transaction,
            actor,
            data.theme_preference,
            data.expected_revision,
        )
    except service.RevisionConflict as conflict:
        return JSONResponse({"current": conflict.current}, status_code=409, headers=HEADERS)
    return JSONResponse(current, headers=HEADERS)


@router.get("/onboarding")
async def read_onboarding(request: Request) -> JSONResponse:
    actor, transaction = await _actor(request, mutating=False)
    current = await run_db(onboarding.get_onboarding, transaction, actor)
    return JSONResponse(current, headers=HEADERS)


@router.put("/onboarding")
async def put_onboarding(request: Request, data: onboarding.OnboardingInput) -> JSONResponse:
    actor, transaction = await _actor(request, mutating=True)
    try:
        current = await run_db(onboarding.save_onboarding, transaction, actor, data)
    except service.RevisionConflict as conflict:
        return JSONResponse({"current": conflict.current}, status_code=409, headers=HEADERS)
    return JSONResponse(current, headers=HEADERS)
