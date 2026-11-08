import asyncio
import json
from collections.abc import Callable, Mapping
from math import isfinite
from urllib.parse import urlsplit

import httpx

from studio.auth.provider_http import read_provider_body


class SupabaseAuthError(Exception):
    def __init__(
        self,
        *,
        status: int | None = None,
        code: str | None = None,
        transport_kind: str | None = None,
    ) -> None:
        self.status = status
        self.code = code
        self.transport_kind = transport_kind
        super().__init__("Supabase Auth request failed")


class SupabaseAuthAdapter:
    """Stateless HTTP boundary; each operation owns and closes its HTTP client."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout: float = 5.0,
        client_factory: Callable[..., httpx.AsyncClient] = httpx.AsyncClient,
    ) -> None:
        parsed = urlsplit(base_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or not api_key
            or not isfinite(timeout)
            or timeout <= 0
            or (
                parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            )
        ):
            raise ValueError("Invalid Supabase Auth adapter configuration")
        self._base_url = base_url.rstrip("/") + "/auth/v1"
        self._api_key = api_key
        self._timeout = timeout
        self._client_factory = client_factory

    async def request(
        self,
        path: str,
        payload: Mapping[str, object],
        *,
        access_token: str | None = None,
        method: str = "POST",
    ) -> dict[str, object] | None:
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("Auth endpoint path must be relative to the provider")

        headers = {
            "apikey": self._api_key,
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        }
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        try:
            # HTTPX's inactivity timeout alone permits indefinitely slow responses.
            async with asyncio.timeout(self._timeout):
                async with (
                    self._client_factory(
                        base_url=self._base_url,
                        timeout=self._timeout,
                        follow_redirects=False,
                        trust_env=False,
                    ) as client,
                    client.stream(
                        method, f"{self._base_url}{path}", json=dict(payload), headers=headers
                    ) as response,
                ):
                    body = await read_provider_body(response)
        except (httpx.TimeoutException, TimeoutError):
            raise SupabaseAuthError(transport_kind="timeout") from None
        except httpx.RequestError:
            raise SupabaseAuthError(transport_kind="unavailable") from None

        if not response.is_success:
            code = None
            try:
                value = json.loads(body)
                if isinstance(value, Mapping):
                    raw_code = value.get("error_code") or value.get("code")
                    if isinstance(raw_code, str):
                        code = raw_code.lower()
            except (ValueError, TypeError, RecursionError):
                pass
            raise SupabaseAuthError(status=response.status_code, code=code)

        if response.status_code == 204 or not body:
            return None
        try:
            value = json.loads(body)
        except (ValueError, RecursionError):
            raise SupabaseAuthError(transport_kind="unavailable") from None
        if not isinstance(value, Mapping):
            raise SupabaseAuthError(transport_kind="unavailable")
        return dict(value)
