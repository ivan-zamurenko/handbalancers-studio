"""Recovery is a separate command, never a source of ordinary session cookies."""

from fastapi import APIRouter, Request
from pydantic import Field, SecretStr, field_validator
from sqlalchemy.exc import SQLAlchemyError
from starlette.responses import JSONResponse

from studio.auth.gateway import AuthFailure
from studio.auth.jwt import InvalidIdentity
from studio.auth.oauth import OAuthRateLimited
from studio.auth.oauth_routes import HEADERS, secure, session_name
from studio.auth.recovery import confirm_recovery, request_recovery
from studio.auth.routes import same_origin
from studio.auth.token_store import StoreError
from studio.auth.verification_routes import (
    EmailInput,
    VerificationInput,
    client_key,
    service_for,
    translate,
)

router = APIRouter(prefix="/api/auth/recovery")


class RecoveryInput(VerificationInput):
    password: SecretStr = Field(repr=False)

    @field_validator("password")
    @classmethod
    def bounded_password(cls, value: SecretStr) -> SecretStr:
        if not 8 <= len(value.get_secret_value()) <= 256:
            raise ValueError("Invalid password length")
        return value


@router.post("/request")
async def request_password_recovery(request: Request, data: EmailInput) -> JSONResponse:
    same_origin(request)
    try:
        await request_recovery(service_for(request), data.email, client_key=client_key(request))
    except (AuthFailure, OAuthRateLimited) as error:
        raise translate(error) from None
    return JSONResponse({"state": "recovery_pending"}, status_code=202, headers=HEADERS)


@router.post("/confirm")
async def confirm_password_recovery(request: Request, data: RecoveryInput) -> JSONResponse:
    same_origin(request)
    try:
        await confirm_recovery(
            service_for(request),
            data.email,
            data.token.get_secret_value(),
            data.password.get_secret_value(),
            client_key=client_key(request),
        )
    except (AuthFailure, InvalidIdentity, OAuthRateLimited, StoreError) as error:
        raise translate(error) from None
    except SQLAlchemyError:
        from fastapi import HTTPException

        raise HTTPException(503, headers={"Retry-After": "5"}) from None
    response = JSONResponse({"state": "password_changed", "login_required": True}, headers=HEADERS)
    response.delete_cookie(
        session_name(request), path="/", secure=secure(request), httponly=True, samesite="lax"
    )
    return response
