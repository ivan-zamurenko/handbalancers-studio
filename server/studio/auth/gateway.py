from enum import StrEnum
from typing import ClassVar

from studio.auth.supabase_adapter import SupabaseAuthAdapter, SupabaseAuthError


class AuthFailureKind(StrEnum):
    ACCOUNT_EXISTS = "account_exists"
    TIMEOUT = "timeout"
    INVALID_CREDENTIALS = "invalid_credentials"
    RATE_LIMIT = "rate_limit"
    UNAVAILABLE = "unavailable"
    REJECTED = "rejected"


class AuthFailure(Exception):
    _messages: ClassVar[dict[AuthFailureKind, str]] = {
        AuthFailureKind.ACCOUNT_EXISTS: "Authentication request cannot create an identity",
        AuthFailureKind.TIMEOUT: "Authentication provider timed out",
        AuthFailureKind.INVALID_CREDENTIALS: "Authentication credentials were rejected",
        AuthFailureKind.RATE_LIMIT: "Authentication provider rate limited the request",
        AuthFailureKind.UNAVAILABLE: "Authentication provider is unavailable",
        AuthFailureKind.REJECTED: "Authentication provider rejected the request",
    }

    def __init__(self, kind: AuthFailureKind) -> None:
        self.kind = kind
        super().__init__(self._messages[kind])


def _classify(error: SupabaseAuthError) -> AuthFailureKind:
    if error.code in {"user_already_exists", "email_exists"}:
        return AuthFailureKind.ACCOUNT_EXISTS
    if error.transport_kind == "timeout":
        return AuthFailureKind.TIMEOUT
    if error.status == 429 or error.code in {"over_request_rate_limit", "too_many_requests"}:
        return AuthFailureKind.RATE_LIMIT
    if error.status in {400, 401, 422} and error.code in {"invalid_credentials", "invalid_grant"}:
        return AuthFailureKind.INVALID_CREDENTIALS
    if error.transport_kind == "unavailable" or (error.status is not None and error.status >= 500):
        return AuthFailureKind.UNAVAILABLE
    return AuthFailureKind.REJECTED


class AuthGateway:
    """Application-facing Auth operations; credentials are sent only to its adapter."""

    def __init__(self, adapter: SupabaseAuthAdapter) -> None:
        self._adapter = adapter

    async def _call(
        self, path: str, payload: dict[str, object], *, access_token: str | None = None
    ) -> dict[str, object] | None:
        try:
            return await self._adapter.request(path, payload, access_token=access_token)
        except SupabaseAuthError as error:
            raise AuthFailure(_classify(error)) from None

    async def signup(
        self, email: str, password: str, first_name: str, last_name: str
    ) -> dict[str, object] | None:
        return await self._call(
            "/signup",
            {
                "email": email,
                "password": password,
                "data": {"first_name": first_name, "last_name": last_name},
            },
        )

    async def verify_email(self, email: str, token: str) -> dict[str, object] | None:
        return await self._call("/verify", {"email": email, "token": token, "type": "signup"})

    async def password_login(self, email: str, password: str) -> dict[str, object] | None:
        return await self._call(
            "/token?grant_type=password", {"email": email, "password": password}
        )

    async def oauth_exchange(self, auth_code: str, code_verifier: str) -> dict[str, object] | None:
        return await self._call(
            "/token?grant_type=pkce",
            {
                "auth_code": auth_code,
                "code_verifier": code_verifier,
            },
        )

    async def refresh(self, refresh_token: str) -> dict[str, object] | None:
        return await self._call("/token?grant_type=refresh_token", {"refresh_token": refresh_token})

    async def logout(self, access_token: str) -> dict[str, object] | None:
        return await self._call("/logout", {}, access_token=access_token)

    async def recovery(self, email: str) -> dict[str, object] | None:
        return await self._call("/recover", {"email": email})
