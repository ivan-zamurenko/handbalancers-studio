"""Signup orchestration: commit private abuse budgets before provider I/O."""

from studio.auth.db_work import run_db
from studio.auth.gateway import AuthFailure, AuthFailureKind
from studio.auth.oauth import OAuthService
from studio.auth.schemas import SignupInput
from studio.auth.verification import quota


async def register(service: OAuthService, data: SignupInput, *, client_key: str) -> None:
    await run_db(quota, service, "register", data.email, client_key)
    try:
        await service.gateway.signup(
            data.email, data.password.get_secret_value(), data.first_name, data.last_name
        )
    except AuthFailure as error:
        if error.kind != AuthFailureKind.ACCOUNT_EXISTS:
            raise
    # A successful signup, including an existing identity, is always pending.
    # Never consume returned tokens or create a product profile here.
