"""Password login uses the same verified identity/session transaction as OAuth."""

from studio.auth.oauth import OAuthResult, OAuthService
from studio.auth.verification import quota


async def password_login(
    service: OAuthService,
    email: str,
    password: str,
    *,
    client_key: str,
    old_cookie: str | None = None,
) -> OAuthResult:
    quota(service, "password-login", email, client_key)
    payload = await service.gateway.password_login(email, password)
    return await service.accept_identity(payload, old_cookie=old_cookie)
