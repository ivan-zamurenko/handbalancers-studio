"""HTTP-only translation of server-owned OAuth; no provider tokens reach JS."""

import hashlib
import re
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import SQLAlchemyError
from starlette.responses import JSONResponse, RedirectResponse

from studio.auth.csrf import require_csrf
from studio.auth.db_work import run_db
from studio.auth.gateway import AuthFailure
from studio.auth.jwt import InvalidIdentity
from studio.auth.oauth import OAuthRateLimited, OAuthService
from studio.auth.refresh import RefreshUnavailable
from studio.auth.routes import same_origin
from studio.auth.token_store import StoreError

router = APIRouter()
HEADERS = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}


class StartInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    return_to: str = "/plans"


def service_for(request: Request) -> OAuthService:
    service = getattr(request.app.state, "oauth_service", None)
    if not isinstance(service, OAuthService):
        raise HTTPException(503)
    return service


def secure(request: Request) -> bool:
    return str(request.app.state.settings.public_origin).startswith("https://")


def session_name(request: Request) -> str:
    return "__Host-studio_session" if secure(request) else "studio_local_session"


def binding_name(request: Request, attempt: str) -> str:
    prefix = "__Host-" if secure(request) else "local_"
    return prefix + "studio_oauth_" + hashlib.sha256(attempt.encode()).hexdigest()[:24]


@router.post("/api/auth/oauth/{provider}/start")
def start(request: Request, provider: str, data: StartInput) -> JSONResponse:
    same_origin(request)
    service = service_for(request)
    if provider not in service.providers:
        raise HTTPException(503)
    try:
        result = service.start(
            provider,
            data.return_to,
            client_key=request.client.host if request.client else "unknown",
        )
    except OAuthRateLimited:
        raise HTTPException(429, headers={"Retry-After": "60"}) from None
    except (ValueError, StoreError):
        raise HTTPException(422) from None
    response = JSONResponse({"authorization_url": result.authorization_url}, headers=HEADERS)
    response.set_cookie(
        binding_name(request, result.attempt),
        result.binding.get_secret_value(),
        max_age=300,
        httponly=True,
        secure=secure(request),
        samesite="lax",
        path="/",
    )
    return response


@router.get("/auth/callback", include_in_schema=False)
async def callback(request: Request) -> RedirectResponse:
    query = request.query_params
    attempt = query.get("attempt", "")
    cookie_name = binding_name(request, attempt)
    response = RedirectResponse("/login?oauth=failed", status_code=303, headers=HEADERS)
    try:
        service = service_for(request)
    except HTTPException:
        return RedirectResponse("/login?oauth=unavailable", status_code=303, headers=HEADERS)
    try:
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", attempt) or any(
            len(query.getlist(key)) != 1 for key in ("attempt", "provider")
        ):
            raise InvalidIdentity()
        binding = request.cookies.get(cookie_name, "")
        provider = query.get("provider", "")
        if query.get("error"):
            await run_db(service.cancel, provider, attempt, binding)
            response = RedirectResponse("/login?oauth=cancelled", status_code=303, headers=HEADERS)
        else:
            if len(query.getlist("code")) != 1:
                raise InvalidIdentity()
            result = await service.finish(
                provider,
                attempt,
                binding,
                query.get("code", ""),
                request.cookies.get(session_name(request)),
            )
            response = RedirectResponse(result.return_path, status_code=303, headers=HEADERS)
            response.set_cookie(
                session_name(request),
                result.cookie.get_secret_value(),
                httponly=True,
                secure=secure(request),
                samesite="lax",
                path="/",
            )
    except (StoreError, InvalidIdentity, AuthFailure, ValueError):
        pass
    response.delete_cookie(
        cookie_name, path="/", secure=secure(request), httponly=True, samesite="lax"
    )
    return response


@router.get("/api/session")
async def session_snapshot(request: Request) -> JSONResponse:
    cookie = request.cookies.get(session_name(request))
    if not cookie:
        return JSONResponse({"authenticated": False}, headers=HEADERS)
    try:
        profile = await service_for(request).session_profile(cookie)
    except (StoreError, InvalidIdentity):
        return JSONResponse({"authenticated": False}, status_code=401, headers=HEADERS)
    except RefreshUnavailable:
        return JSONResponse(
            {"detail": "Session temporarily unavailable"}, status_code=503, headers=HEADERS
        )
    # No paid access is inferred from identity. Entitlement module is not ready.
    return JSONResponse(
        {
            "authenticated": True,
            "user": profile,
            "setup_required": await _setup_required(request, profile),
            "entitlements": [],
            "csrf_token": service_for(request).csrf_token(cookie),
        },
        headers=HEADERS,
    )


async def _setup_required(request: Request, profile: dict[str, object]) -> bool:
    """Name + questionnaire done? Read as studio_web; never blocks the session snapshot."""
    from studio.accounts.onboarding import setup_required
    from studio.db import UnsafeWebRole
    from studio.shared.context import Actor

    transaction = getattr(request.app.state, "web_transaction", None)
    if transaction is None:
        return not profile.get("profile_complete")
    try:
        return await run_db(setup_required, transaction, Actor(UUID(str(profile["id"]))))
    except (SQLAlchemyError, UnsafeWebRole):
        return not profile.get("profile_complete")


@router.post("/api/auth/logout")
async def logout(request: Request):
    from starlette.responses import Response

    same_origin(request)
    service = service_for(request)
    cookie = request.cookies.get(session_name(request), "")
    if not cookie:
        raise HTTPException(403)
    require_csrf(request, service.csrf_token(cookie))
    await service.logout(cookie)
    response = Response(status_code=204, headers=HEADERS)
    response.delete_cookie(
        session_name(request), path="/", secure=secure(request), httponly=True, samesite="lax"
    )
    return response
