"""Thin HTTP translation. Only configured server-side gateway is trusted."""

from fastapi import APIRouter, HTTPException, Request
from starlette.responses import JSONResponse

from studio.auth.gateway import AuthFailure, AuthFailureKind, AuthGateway
from studio.auth.schemas import SignupInput
from studio.auth.service import register

router = APIRouter(prefix="/api/auth")


def same_origin(request: Request) -> None:
    expected = request.app.state.settings.public_origin
    if not expected or request.headers.get("origin") != expected.rstrip("/"):
        raise HTTPException(403)


def gateway_for(request: Request) -> AuthGateway:
    gateway = getattr(request.app.state, "auth_gateway", None)
    if not isinstance(gateway, AuthGateway):
        raise HTTPException(503)
    return gateway


@router.post("/register")
async def signup(request: Request, data: SignupInput) -> JSONResponse:
    same_origin(request)
    try:
        await register(gateway_for(request), data)
    except AuthFailure as error:
        if error.kind == AuthFailureKind.RATE_LIMIT:
            raise HTTPException(429) from None
        if error.kind in {AuthFailureKind.TIMEOUT, AuthFailureKind.UNAVAILABLE}:
            raise HTTPException(503, headers={"Retry-After": "5"}) from None
        raise HTTPException(422) from None
    return JSONResponse(
        {"state": "verification_pending"}, status_code=202, headers={"Cache-Control": "no-store"}
    )
