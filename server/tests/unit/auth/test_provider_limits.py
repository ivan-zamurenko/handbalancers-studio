import asyncio

import httpx
import pytest
from studio.auth.gateway import AuthFailure, AuthGateway
from studio.auth.supabase_adapter import SupabaseAuthAdapter


class ProviderStream(httpx.AsyncByteStream):
    def __init__(self, chunks, *, delay=0):
        self.chunks = chunks
        self.delay = delay
        self.read_count = 0
        self.closed = False
        self.started = asyncio.Event()

    async def __aiter__(self):
        for chunk in self.chunks:
            self.started.set()
            await asyncio.sleep(self.delay)
            self.read_count += 1
            yield chunk

    async def aclose(self):
        self.closed = True


def adapter_for(
    stream, *, status=200, headers=None, timeout=1, requests=None, clients=None, header_delay=0
):
    async def respond(request):
        if requests is not None:
            requests.append(request)
        await asyncio.sleep(header_delay)
        return httpx.Response(status, stream=stream, headers=headers)

    def client_factory(**options):
        client = httpx.AsyncClient(**options, transport=httpx.MockTransport(respond))
        if clients is not None:
            clients.append(client)
        return client

    return SupabaseAuthAdapter(
        "https://auth.example.test", "public-key", timeout=timeout, client_factory=client_factory
    )


@pytest.mark.parametrize("status", [200, 400, 503])
@pytest.mark.parametrize("length", [None, "1", "65537"])
def test_oversized_provider_body_is_unavailable_and_stops_reading(status, length):
    stream = ProviderStream([b"x" * 32768] * 5)
    headers = {} if length is None else {"content-length": length}
    clients = []
    gateway = AuthGateway(adapter_for(stream, status=status, headers=headers, clients=clients))

    with pytest.raises(AuthFailure) as failure:
        asyncio.run(gateway.password_login("user@example.test", "private-password"))

    assert failure.value.kind == "unavailable"
    assert stream.read_count == (0 if length == "65537" else 3)
    assert stream.closed
    assert all(client.is_closed for client in clients)
    assert "private-password" not in str(failure.value)


def test_total_deadline_stops_slow_provider_chunks_and_closes_transport():
    stream = ProviderStream([b" "] * 20 + [b"{}"], delay=0.01)
    clients = []
    gateway = AuthGateway(adapter_for(stream, timeout=0.05, clients=clients))

    with pytest.raises(AuthFailure) as failure:
        asyncio.run(gateway.password_login("user@example.test", "password"))

    assert failure.value.kind == "timeout"
    assert stream.read_count < 20
    assert stream.closed
    assert all(client.is_closed for client in clients)


def test_total_deadline_includes_waiting_for_response_headers():
    clients = []
    adapter = adapter_for(ProviderStream([b"{}"]), timeout=0.02, header_delay=0.2, clients=clients)
    with pytest.raises(AuthFailure) as failure:
        asyncio.run(AuthGateway(adapter).password_login("user@example.test", "password"))
    assert failure.value.kind == "timeout"
    assert all(client.is_closed for client in clients)


def test_provider_json_at_size_boundary_is_accepted():
    stream = ProviderStream([b'{"value":"', b"a" * (65536 - 12), b'"}'])
    adapter = adapter_for(stream, headers={"content-length": "65536"})
    assert asyncio.run(adapter.request("/token", {})) == {"value": "a" * (65536 - 12)}
    assert stream.closed


@pytest.mark.parametrize("encoding", ["gzip", "deflate", "br", "identity, gzip"])
def test_encoded_provider_body_is_rejected_before_reading(encoding):
    stream = ProviderStream([b"{}"])
    requests = []
    gateway = AuthGateway(
        adapter_for(stream, headers={"content-encoding": encoding}, requests=requests)
    )

    with pytest.raises(AuthFailure) as failure:
        asyncio.run(gateway.password_login("user@example.test", "password"))

    assert failure.value.kind == "unavailable"
    assert stream.read_count == 0
    assert stream.closed
    assert requests[0].headers["accept-encoding"] == "identity"


@pytest.mark.parametrize(
    "status, chunks, expected",
    [(200, [b'{"ok":', b"true}"], {"ok": True}), (204, [], None), (200, [], None)],
)
def test_bounded_streamed_success_preserves_response_contract(status, chunks, expected):
    stream = ProviderStream(chunks)
    adapter = adapter_for(stream, status=status)
    assert asyncio.run(adapter.request("/token", {})) == expected
    assert stream.closed


def test_bounded_streamed_error_preserves_provider_classification():
    stream = ProviderStream([b'{"error_code":', b'"invalid_credentials"}'])
    gateway = AuthGateway(adapter_for(stream, status=400))
    with pytest.raises(AuthFailure) as failure:
        asyncio.run(gateway.password_login("user@example.test", "password"))
    assert failure.value.kind == "invalid_credentials"
    assert stream.closed


@pytest.mark.parametrize(
    "body",
    [b"{", b"[]", b"[" * 20000 + b"]" * 20000],
    ids=["invalid-syntax", "non-mapping", "excessive-nesting"],
)
def test_malformed_success_is_unavailable_not_credential_rejection(body):
    stream = ProviderStream([body])
    gateway = AuthGateway(adapter_for(stream))
    with pytest.raises(AuthFailure) as failure:
        asyncio.run(gateway.refresh("private-refresh-token"))
    assert failure.value.kind == "unavailable"
    assert "private-refresh-token" not in str(failure.value)
    assert stream.closed


@pytest.mark.parametrize(
    "status, expected_kind", [(400, "rejected"), (401, "rejected"), (503, "unavailable")]
)
def test_deeply_nested_error_json_preserves_http_failure_semantics(status, expected_kind):
    stream = ProviderStream([b"[" * 20000 + b"]" * 20000])
    gateway = AuthGateway(adapter_for(stream, status=status))
    with pytest.raises(AuthFailure) as failure:
        asyncio.run(gateway.refresh("private-refresh-token"))
    assert failure.value.kind == expected_kind
    assert stream.closed


def test_external_cancellation_propagates_and_closes_provider_stream():
    async def run():
        stream = ProviderStream([b"{}"], delay=10)
        adapter = adapter_for(stream)
        request = asyncio.create_task(adapter.request("/token", {}))
        await stream.started.wait()
        request.cancel()
        with pytest.raises(asyncio.CancelledError):
            await request
        assert stream.closed

    asyncio.run(run())
