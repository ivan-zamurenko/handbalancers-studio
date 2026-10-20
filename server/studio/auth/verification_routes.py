"""Thin same-origin email verification endpoints with opaque session cookies."""

import re

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from starlette.responses import JSONResponse

from studio.auth.gateway import AuthFailure, AuthFailureKind
from studio.auth.jwt import InvalidIdentity
from studio.auth.oauth import OAuthRateLimited, OAuthService
from studio.auth.oauth_routes import HEADERS, secure, session_name
from studio.auth.routes import same_origin
from studio.auth.schemas import Email
from studio.auth.sessions import password_login
from studio.auth.token_store import StoreError
from studio.auth.verification import resend, verify_email

router = APIRouter(prefix="/api/auth")


class EmailInput(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    email: Email


class VerificationInput(EmailInput):
    token: SecretStr = Field(repr=False)

    @field_validator("token")
    @classmethod
    def six_digits(cls, value: SecretStr) -> SecretStr:
        if re.fullmatch(r"[0-9]{6}", value.get_secret_value()) is None:
            raise ValueError("Expected six-digit code")
        return value


def service_for(request: Request) -> OAuthService:
    service = getattr(request.app.state, "verification_service", None)
    if not isinstance(service, OAuthService):
        raise HTTPException(503)
    return service


def client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def translate(error: Exception) -> HTTPException:
    if isinstance(error, OAuthRateLimited) or (
        isinstance(error, AuthFailure) and error.kind == AuthFailureKind.RATE_LIMIT
    ):
        return HTTPException(429, headers={"Retry-After": "60"})
    if isinstance(error, AuthFailure) and error.kind in {
        AuthFailureKind.UNAVAILABLE,
        AuthFailureKind.TIMEOUT,
    }:
        return HTTPException(503, headers={"Retry-After": "5"})
    return HTTPException(422)


@router.post("/verify-email")
async def verify(request: Request, data: VerificationInput) -> JSONResponse:
    same_origin(request)
    service = service_for(request)
    try:
        result = await verify_email(
            service,
            data.email,
            data.token.get_secret_value(),
            client_key=client_key(request),
            old_cookie=request.cookies.get(session_name(request)),
        )
    except (AuthFailure, InvalidIdentity, StoreError, OAuthRateLimited) as error:
        raise translate(error) from None
    response = JSONResponse(
        {"state": "authenticated", "profile_complete": result.profile_complete}, headers=HEADERS
    )
    response.set_cookie(
        session_name(request),
        result.cookie.get_secret_value(),
        httponly=True,
        secure=secure(request),
        samesite="lax",
        path="/",
    )
    return response


@router.post("/resend-verification")
async def resend_verification(request: Request, data: EmailInput) -> JSONResponse:
    same_origin(request)
    try:
        await resend(service_for(request), data.email, client_key=client_key(request))
    except (AuthFailure, OAuthRateLimited) as error:
        raise translate(error) from None
    return JSONResponse({"state": "verification_pending"}, status_code=202, headers=HEADERS)


class LoginInput(EmailInput):
    password: SecretStr = Field(repr=False)

    @field_validator("password")
    @classmethod
    def bounded_password(cls, value: SecretStr) -> SecretStr:
        if not 1 <= len(value.get_secret_value()) <= 256:
            raise ValueError("Invalid password length")
        return value


@router.post("/login")
async def login(request: Request, data: LoginInput) -> JSONResponse:
    same_origin(request)
    try:
        result = await password_login(
            service_for(request),
            data.email,
            data.password.get_secret_value(),
            client_key=client_key(request),
            old_cookie=request.cookies.get(session_name(request)),
        )
    except (AuthFailure, InvalidIdentity, StoreError, OAuthRateLimited) as error:
        failure = translate(error)
        # Unknown email, wrong password, unconfirmed and inactive identity are indistinguishable.
        if failure.status_code == 422:
            failure = HTTPException(401)
        raise failure from None
    response = JSONResponse(
        {"state": "authenticated", "profile_complete": result.profile_complete}, headers=HEADERS
    )
    response.set_cookie(
        session_name(request),
        result.cookie.get_secret_value(),
        httponly=True,
        secure=secure(request),
        samesite="lax",
        path="/",
    )
    return response
