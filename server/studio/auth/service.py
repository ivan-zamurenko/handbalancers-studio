"""Auth orchestration; signup deliberately has no product database dependency."""

from studio.auth.gateway import AuthFailure, AuthFailureKind, AuthGateway
from studio.auth.schemas import SignupInput


async def register(gateway: AuthGateway, data: SignupInput) -> None:
    try:
        await gateway.signup(
            data.email, data.password.get_secret_value(), data.first_name, data.last_name
        )
    except AuthFailure as error:
        if error.kind != AuthFailureKind.ACCOUNT_EXISTS:
            raise
    # A successful signup, including an existing identity, is always pending.
    # Never consume returned tokens or create a product profile here.
