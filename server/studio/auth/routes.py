"""Thin HTTP translation. Only configured server-side gateway is trusted."""

from fastapi import APIRouter, HTTPException, Request
from starlette.responses import JSONResponse

from studio.auth.csrf import same_origin
from studio.auth.gateway import AuthFailure, AuthFailureKind
from studio.auth.oauth import OAuthRateLimited, OAuthService
from studio.auth.schemas import SignupInput
from studio.auth.service import register

router = APIRouter(prefix="/api/auth")


def service_for(request: Request) -> OAuthService:
    service = getattr(request.app.state, "verification_service", None)
    if not isinstance(service, OAuthService):
        raise HTTPException(503)
    return service


@router.post("/register")
async def signup(request: Request, data: SignupInput) -> JSONResponse:
    same_origin(request)
    try:
        await register(
            service_for(request),
            data,
            client_key=request.client.host if request.client else "unknown",
        )
    except OAuthRateLimited:
        raise HTTPException(429, headers={"Retry-After": "60"}) from None
    except AuthFailure as error:
        if error.kind == AuthFailureKind.RATE_LIMIT:
            raise HTTPException(429, headers={"Retry-After": "60"}) from None
        if error.kind in {AuthFailureKind.TIMEOUT, AuthFailureKind.UNAVAILABLE}:
            raise HTTPException(503, headers={"Retry-After": "5"}) from None
        raise HTTPException(422) from None
    return JSONResponse(
        {"state": "verification_pending"}, status_code=202, headers={"Cache-Control": "no-store"}
    )
