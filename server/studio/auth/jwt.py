"""Verify identity only; product role/active/session revocation remain DB checks."""

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import UUID

import httpx
import jwt

from studio.auth.provider_http import read_provider_body


class InvalidIdentity(Exception):
    def __init__(self) -> None:
        super().__init__("Authentication identity could not be verified")


class IdentityVerificationUnavailable(InvalidIdentity):
    """Missing trusted keys are not evidence that an existing session is invalid."""


@dataclass(frozen=True)
class VerifiedIdentity:
    user_id: UUID
    session_id: UUID
    expires_at: int


class JWTValidator:
    """ES256/RS256 allowlist. JWKS TTL 300s, refresh at most once per 30s.

    Unknown kids fail closed during cooldown, including after failed fetches.
    A singleflight lock covers JWKS fetch only; it never holds a DB transaction.
    """

    def __init__(
        self,
        *,
        issuer: str,
        fetch_jwks: Callable[[], Awaitable[dict[str, object]]] | None = None,
    ) -> None:
        from urllib.parse import urlsplit

        url = urlsplit(issuer)
        if (
            url.scheme not in {"https", "http"}
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
            or (url.scheme == "http" and url.hostname not in {"127.0.0.1", "localhost", "::1"})
        ):
            raise ValueError("Invalid trusted JWT issuer")
        self.issuer = issuer.rstrip("/")
        self._fetch = fetch_jwks or self._fetch_http
        self._keys: dict[str, jwt.PyJWK] = {}
        self._updated = float("-inf")
        self._attempted = float("-inf")
        self._last_fetch_failed = False
        self._lock = asyncio.Lock()

    async def _fetch_http(self) -> dict[str, object]:
        async with (
            httpx.AsyncClient(timeout=5, follow_redirects=False, trust_env=False) as client,
            client.stream(
                "GET",
                self.issuer + "/.well-known/jwks.json",
                headers={"Accept-Encoding": "identity"},
            ) as response,
        ):
            response.raise_for_status()
            value = json.loads(await read_provider_body(response))
            if not isinstance(value, dict):
                raise IdentityVerificationUnavailable()
            return value

    async def _key(self, kid: str) -> jwt.PyJWK:
        async with self._lock:
            now = time.monotonic()
            if (
                kid not in self._keys or now - self._updated >= 300
            ) and now - self._attempted >= 30:
                self._attempted = now
                self._last_fetch_failed = True
                try:
                    async with asyncio.timeout(5):
                        payload = await self._fetch()
                    raw_keys = payload.get("keys")
                    if not isinstance(raw_keys, list) or len(raw_keys) > 100:
                        raise IdentityVerificationUnavailable()
                    keys = {}
                    for raw in raw_keys:
                        if not isinstance(raw, dict) or not isinstance(raw.get("kid"), str):
                            continue
                        if (
                            raw.get("alg") not in {"ES256", "RS256"}
                            or raw.get("use", "sig") != "sig"
                        ):
                            continue
                        if raw["kid"] in keys:
                            raise IdentityVerificationUnavailable()
                        keys[raw["kid"]] = jwt.PyJWK.from_dict(raw)
                    if not keys:
                        raise IdentityVerificationUnavailable()
                    self._keys = keys
                    self._updated = now
                    self._last_fetch_failed = False
                except (httpx.HTTPError, TimeoutError, ValueError, RecursionError, jwt.PyJWTError):
                    raise IdentityVerificationUnavailable() from None
            if now - self._updated >= 300:
                raise IdentityVerificationUnavailable()
            if kid not in self._keys:
                if self._last_fetch_failed:
                    raise IdentityVerificationUnavailable()
                raise InvalidIdentity()
            return self._keys[kid]

    async def verify(self, token: str) -> VerifiedIdentity:
        try:
            if len(token) > 16384:
                raise InvalidIdentity()
            header = jwt.get_unverified_header(token)
            algorithm, kid = header.get("alg"), header.get("kid")
            if algorithm not in {"ES256", "RS256"} or not isinstance(kid, str) or not kid:
                raise InvalidIdentity()
            key = await self._key(kid)
            if key.algorithm_name != algorithm:
                raise InvalidIdentity()
            claims = jwt.decode(
                token,
                key.key,
                algorithms=[algorithm],
                issuer=self.issuer,
                audience="authenticated",
                options={"require": ["exp", "iat", "sub", "iss", "aud", "session_id"]},
            )
            if type(claims["exp"]) is not int or type(claims["iat"]) is not int:
                raise InvalidIdentity()
            return VerifiedIdentity(UUID(claims["sub"]), UUID(claims["session_id"]), claims["exp"])
        except (jwt.PyJWTError, ValueError, TypeError, AttributeError):
            raise InvalidIdentity() from None
