"""Server PKCE orchestration: consume/commit before network, then provision/session."""

import base64
import hashlib
import hmac
import secrets
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode
from uuid import UUID

from pydantic import SecretStr
from sqlalchemy.orm import Session

from studio.accounts.provisioning import current_profile, provision
from studio.auth.gateway import AuthGateway
from studio.auth.jwt import InvalidIdentity, JWTValidator
from studio.auth.rate_limit import allow_start
from studio.auth.token_store import TokenStore


@dataclass(frozen=True)
class OAuthStart:
    authorization_url: str = field(repr=False)
    attempt: str = field(repr=False)
    binding: SecretStr


@dataclass(frozen=True)
class OAuthResult:
    user_id: UUID
    cookie: SecretStr
    return_path: str
    profile_complete: bool


class OAuthRateLimited(Exception):
    pass


class OAuthService:
    def __init__(
        self,
        *,
        auth_transaction: Callable[[], AbstractContextManager[Session]],
        store: TokenStore,
        gateway: AuthGateway,
        validator: JWTValidator,
        supabase_url: str,
        public_origin: str,
        providers: frozenset[str],
        secret: bytes | None = None,
    ):
        self.transaction = auth_transaction
        self.store = store
        self.gateway = gateway
        self.validator = validator
        self.supabase_url = supabase_url.rstrip("/")
        self.public_origin = public_origin.rstrip("/")
        self.providers = providers
        self.secret = secret or secrets.token_bytes(32)

    def start(self, provider: str, return_path: str, *, client_key: str = "direct") -> OAuthStart:
        if provider not in {"google", "apple"} or provider not in self.providers:
            raise ValueError("Provider unavailable")
        bucket = hmac.new(
            self.secret, ("oauth-start:" + client_key).encode(), hashlib.sha256
        ).hexdigest()
        with self.transaction() as session:
            allowed = allow_start(session, bucket)
        if not allowed:
            raise OAuthRateLimited()
        verifier = secrets.token_urlsafe(48)
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .decode()
            .rstrip("=")
        )
        with self.transaction() as session:
            handle = self.store.create_attempt(
                session,
                provider=provider,
                verifier=verifier,
                allowed_return_path=return_path,
                expires_at=datetime.now(UTC) + timedelta(minutes=5),
            )
        attempt = handle.state.get_secret_value()
        callback = (
            self.public_origin
            + "/auth/callback?"
            + urlencode({"attempt": attempt, "provider": provider})
        )
        url = (
            self.supabase_url
            + "/auth/v1/authorize?"
            + urlencode(
                {
                    "provider": provider,
                    "redirect_to": callback,
                    "code_challenge": challenge,
                    "code_challenge_method": "s256",
                }
            )
        )
        return OAuthStart(url, attempt, handle.binding)

    def cancel(self, provider: str, attempt: str, binding: str) -> None:
        with self.transaction() as session:
            self.store.consume_attempt(session, attempt, provider=provider, binding=binding)

    async def finish(
        self, provider: str, attempt: str, binding: str, code: str, old_cookie: str | None = None
    ) -> OAuthResult:
        if provider not in self.providers or not code or len(code) > 4096:
            raise InvalidIdentity()
        # Complete transaction before exchange. A timeout requires a new attempt;
        # callbacks are never retried with an already consumed code/verifier.
        with self.transaction() as session:
            pending = self.store.consume_attempt(
                session, attempt, provider=provider, binding=binding
            )
        payload = await self.gateway.oauth_exchange(code, pending.verifier.get_secret_value())
        if not isinstance(payload, dict):
            raise InvalidIdentity()
        access, refresh, user = (
            payload.get("access_token"),
            payload.get("refresh_token"),
            payload.get("user"),
        )
        if (
            not isinstance(access, str)
            or not isinstance(refresh, str)
            or not refresh
            or not isinstance(user, dict)
            or not user.get("email_confirmed_at")
        ):
            raise InvalidIdentity()
        identity = await self.validator.verify(access)
        if user.get("id") != str(identity.user_id):
            raise InvalidIdentity()
        with self.transaction() as session:
            profile = provision(session, identity, metadata=user.get("user_metadata"))
            handle = self.store.create_session(
                session,
                user_id=handle_user_id(profile),
                upstream_session_id=identity.session_id,
                access_token=access,
                refresh_token=refresh,
                access_expires_at=datetime.fromtimestamp(identity.expires_at, UTC),
                expires_at=datetime.fromtimestamp(identity.expires_at, UTC),
            )
            if old_cookie:
                self.store.revoke_session(session, old_cookie)
        return OAuthResult(
            handle_user_id(profile),
            handle.cookie,
            pending.allowed_return_path,
            bool(profile["first_name"] and profile["last_name"]),
        )

    async def session_profile(self, cookie: str) -> dict[str, object]:
        with self.transaction() as session:
            tokens = self.store.read_session(session, cookie)
        identity = await self.validator.verify(tokens.access_token.get_secret_value())
        # Recheck local revocation after network/JWKS wait; current active role from DB.
        with self.transaction() as session:
            current = self.store.read_session(session, cookie)
            profile = current_profile(session, current.user_id)
            if (
                identity.user_id != profile["auth_user_id"]
                or identity.session_id != current.upstream_session_id
            ):
                raise InvalidIdentity()
        profile.pop("auth_user_id")
        profile["id"] = str(profile["id"])
        profile["profile_complete"] = bool(profile["first_name"] and profile["last_name"])
        return profile

    def csrf_token(self, cookie: str) -> str:
        return hmac.new(
            self.secret, ("session-csrf:" + cookie).encode(), hashlib.sha256
        ).hexdigest()

    async def logout(self, cookie: str) -> None:
        from studio.auth.gateway import AuthFailure
        from studio.auth.token_store import StoreError

        with self.transaction() as session:
            try:
                tokens = self.store.read_session(session, cookie)
            except StoreError:
                return
            self.store.revoke_session(session, cookie)
        # Local revocation is committed even if Supabase is unreachable.
        try:
            await self.gateway.logout(tokens.access_token.get_secret_value())
        except AuthFailure:
            pass


def handle_user_id(profile: dict[str, object]) -> UUID:
    value = profile["id"]
    if not isinstance(value, UUID):
        raise InvalidIdentity()
    return value
