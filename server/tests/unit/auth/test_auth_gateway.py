import asyncio
import logging
from urllib.parse import parse_qs

import httpx
import pytest
from studio.auth.gateway import AuthFailure, AuthGateway
from studio.auth.supabase_adapter import SupabaseAuthAdapter


def gateway_for(handler, *, clients=None):
    def client_factory(**options):
        client = httpx.AsyncClient(**options, transport=httpx.MockTransport(handler))
        if clients is not None:
            clients.append(client)
        return client

    adapter = SupabaseAuthAdapter(
        "https://auth.example.test",
        "public-anon-key",
        client_factory=client_factory,
    )
    return AuthGateway(adapter)


def test_request_scoped_auth():
    requests = []
    clients = []

    def respond(request):
        requests.append(request)
        if request.url.path == "/auth/v1/signup":
            return httpx.Response(
                200, json={"user": {"id": "user-1"}}, headers={"set-cookie": "session=signup"}
            )
        return httpx.Response(200, json={"access_token": "access", "refresh_token": "refresh"})

    gateway = gateway_for(respond, clients=clients)

    async def run_concurrently():
        await asyncio.gather(
            gateway.signup("one@example.test", "password-one", "One", "User"),
            gateway.password_login("two@example.test", "password-two"),
        )

    asyncio.run(run_concurrently())

    assert len(clients) == 2
    assert clients[0] is not clients[1]
    assert all(request.headers["apikey"] == "public-anon-key" for request in requests)
    login_request = next(request for request in requests if request.url.path == "/auth/v1/token")
    assert "cookie" not in login_request.headers


def test_gateway_exposes_all_auth_flows():
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"ok": True})

    gateway = gateway_for(respond)

    async def run_flows():
        await gateway.signup("user@example.test", "one-time-password", "First", "Last")
        await gateway.verify_email("user@example.test", "123456")
        await gateway.password_login("user@example.test", "one-time-password")
        await gateway.oauth_exchange("auth-code", "pkce-verifier")
        await gateway.refresh("refresh-token")
        await gateway.logout("access-token")
        await gateway.recovery("user@example.test")

    asyncio.run(run_flows())

    assert [request.url.path for request in requests] == [
        "/auth/v1/signup",
        "/auth/v1/verify",
        "/auth/v1/token",
        "/auth/v1/token",
        "/auth/v1/token",
        "/auth/v1/logout",
        "/auth/v1/recover",
    ]
    assert [
        parse_qs(request.url.query.decode()).get("grant_type") for request in requests[2:5]
    ] == [["password"], ["pkce"], ["refresh_token"]]
    logout_request = requests[5]
    assert logout_request.headers["authorization"] == "Bearer access-token"


@pytest.mark.parametrize(
    ("failure", "expected_kind"),
    [
        ("timeout", "timeout"),
        ("invalid_credentials", "invalid_credentials"),
        ("rate_limit", "rate_limit"),
    ],
)
def test_upstream_failure_classified(failure, expected_kind):
    secret = "never-log-this-password"

    def respond(request):
        if failure == "timeout":
            raise httpx.ReadTimeout(secret)
        if failure == "invalid_credentials":
            return httpx.Response(400, json={"code": "invalid_credentials", "msg": secret})
        return httpx.Response(429, json={"msg": secret})

    gateway = gateway_for(respond)
    with pytest.raises(AuthFailure) as raised:
        asyncio.run(gateway.password_login("user@example.test", secret))

    assert raised.value.kind == expected_kind
    assert secret not in str(raised.value)


def test_password_not_persisted(caplog):
    password = "one-time-password-only"

    def respond(request):
        return httpx.Response(400, json={"code": "invalid_credentials", "msg": password})

    gateway = gateway_for(respond)
    with caplog.at_level(logging.DEBUG), pytest.raises(AuthFailure):
        asyncio.run(gateway.password_login("user@example.test", password))

    assert password not in caplog.text
    assert password not in repr(gateway)
    assert not hasattr(gateway, "password")


@pytest.mark.parametrize("timeout", [float("inf"), float("nan"), 0, -1])
def test_timeout_must_be_bounded(timeout):
    with pytest.raises(ValueError):
        SupabaseAuthAdapter("https://auth.example.test", "key", timeout=timeout)


def test_plaintext_remote_credentials_forbidden():
    with pytest.raises(ValueError):
        SupabaseAuthAdapter("http://auth.example.test", "key")


def test_invalid_success_payload_is_failure():
    gateway = gateway_for(lambda request: httpx.Response(200, json=["invalid"]))
    with pytest.raises(AuthFailure):
        asyncio.run(gateway.password_login("user@example.test", "password"))


def test_invalid_credentials_code_is_stable_across_upstream_status():
    gateway = gateway_for(
        lambda request: httpx.Response(422, json={"error_code": "invalid_credentials"})
    )
    with pytest.raises(AuthFailure) as failure:
        asyncio.run(gateway.password_login("user@example.test", "password"))
    assert failure.value.kind == "invalid_credentials"
